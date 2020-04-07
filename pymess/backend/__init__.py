from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _l
from django.utils.timezone import now

from pymess.utils import fullname


class BaseBackend:

    model = None

    def __init__(self):
        assert self.model is not None, _l('self.model cannot be None')

    def _get_extra_sender_data(self):
        """
        Gets arguments that will be saved with the message in the extra_sender_data field
        """
        return {}

    def _get_extra_message_kwargs(self):
        """
        Gets model message kwargs that will be saved with the message
        """
        return {}

    def update_message(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message
        :param message: message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
        :return:
        """
        extra_sender_data = {
            **self._get_extra_sender_data(),
            **({} if extra_sender_data is None else extra_sender_data)
        }
        message.change_and_save(
            backend=fullname(self),
            extra_sender_data=extra_sender_data,
            **kwargs
        )

    def update_message_after_sending(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message after it was sent
        :param message: message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
        :return:
        """
        self.update_message(
            message, extra_sender_data, number_of_send_attempts=message.number_of_send_attempts + 1, **kwargs
        )

    def create_message(self, recipient, content, related_objects, tag, template, **kwargs):
        """
        Create message which will be logged in the database.
        :param recipient: email or phone number of the recipient
        :param content: content of the message
        :param related_objects: list of related objects that will be linked with the message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
        :param kwargs: extra attributes that will be saved with the message
        """
        message = self.model.objects.create(
            recipient=recipient,
            content=content,
            tag=tag,
            template=template,
            template_slug=template.slug if template else None,
            retry_sending=self.get_retry_sending(),
            **kwargs
        )
        if related_objects:
            message.related_objects.create_from_related_objects(*related_objects)
        return message

    def is_turned_on_batch_sending(self):
        return False

    def publish_message(self, message):
        """
        Send the message
        :param message: SMS message
        """
        raise NotImplementedError

    def get_batch_size(self):
        """
        Return number of messages sent in batch
        """
        raise NotImplementedError

    def get_batch_max_number_of_send_attempts(self):
        """
        Return number attempts to send message
        """
        raise NotImplementedError

    def get_batch_max_seconds_to_send(self):
        """
        Return max timeout in seconds to send message
        """
        raise NotImplementedError

    def get_waiting_or_retry_messages(self):
        """
        Return queryset of waiting messages to send
        """
        return self.model.objects.filter(
            Q(state=self.model.STATE.WAITING) |
            Q(
                retry_sending=True,
                state=self.model.STATE.ERROR_NOT_SENT,
                number_of_send_attempts__lte=self.get_batch_max_number_of_send_attempts(),
                created_at__gte=now() - timedelta(seconds=self.get_batch_max_seconds_to_send())
            )
        )

    def get_retry_sending(self):
        """
        Return True if message should be retried if sending fails
        """
        raise NotImplementedError

    def publish_messages(self, messages):
        """
        Sends more messages together. If concrete backend provides send more messages at once the method
        can be overridden
        :param messages: list of messages
        """
        [self.publish_message(message) for message in messages]

    @transaction.atomic
    def send(self, recipient, content, related_objects=None, tag=None, template=None, **kwargs):
        """
        Send message with the text content to the phone number (recipient)
        :param recipient: email or phone number of the recipient
        :param content: text content of the message
        :param related_objects: list of related objects that will be linked with the message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was create
        :param kwargs: extra attributes that will be stored to the message
        """
        message = self.create_message(recipient, content, related_objects, tag, template, **kwargs)
        if not self.is_turned_on_batch_sending():
            self.publish_message(message)
        return message

    @transaction.atomic
    def bulk_send(self, recipients, content, related_objects=None, tag=None, template=None, **kwargs):
        """
        Send more messages in one bulk
        :param recipients: list of emails or phone numbers of recipients
        :param content: text content of the messages
        :param related_objects: list of related objects that will be linked with the message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was create
        :param kwargs: extra attributes that will be stored with messages
        """
        messages = [
            self.create_message(recipient, content, related_objects, tag, template, **kwargs)
            for recipient in recipients
        ]
        self.publish_messages(messages)
        return messages


def send_template(recipient, slug, context_data, related_objects=None, tag=None, template_model=None, **kwargs):
    """
    Helper for building and sending message from a template.
    :param recipient: email or phone number of the recipient
    :param slug: slug of a template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
    :param tag: string mark that will be saved with the message
    :param template_model: template model instance
    :return: dialer message object or None if template cannot be sent
    """

    assert template_model is not None, _l('template_model cannot be None')

    return template_model.objects.get(slug=slug).send(
        recipient,
        context_data,
        related_objects=related_objects,
        tag=tag,
        **kwargs
    )


def send(recipient, content, related_objects=None, tag=None, message_sender=None, **kwargs):
    """
    Helper for sending message.
    :param recipient: email or phone number of the recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :param message_sender: sender instance 
    :return: True if message was successfully sent or False if message is in error state
    """
    return message_sender.send(
        recipient,
        content,
        related_objects=related_objects,
        tag=tag,
        **kwargs
    ).failed
