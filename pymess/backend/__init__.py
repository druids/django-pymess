from attrdict import AttrDict
from collections import OrderedDict, defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _l
from django.utils.timezone import now

from pymess.config import settings
from pymess.config import get_router, get_backend, get_default_sender_backend_name
from pymess.utils import fullname


class BaseController:
    """
    Base class of Controller. Any type of communication requires Controller derived from this class.
    Many backends of the same type of communication can be supported by one controller which chooses the right backend
    implementation based on the recipient
    """

    model = None
    backend_type_name = None

    def __init__(self):
        self._loaded_backends = {}

    def get_backend(self, recipient):
        backend_name = self.router.get_backend_name(recipient) or get_default_sender_backend_name(self.backend_type_name)
        if backend_name not in self._loaded_backends:
            self._loaded_backends[backend_name] = get_backend(self.backend_type_name, backend_name)
        return self._loaded_backends[backend_name]

    @cached_property
    def router(self):
        return get_router(self.backend_type_name)

    def get_waiting_or_retry_messages(self):
        """
        Return queryset of waiting messages to send
        """
        return self.model.objects.filter(state__in={self.model.STATE.WAITING, self.model.STATE.ERROR_RETRY})

    def is_turned_on_batch_sending(self):
        return False

    def publish_or_retry_message(self, message):
        backend = self.get_backend(recipient=message.recipient)
        if (message.number_of_send_attempts > backend.get_batch_max_number_of_send_attempts()
            or message.created_at < now() - timedelta(seconds=self.get_batch_max_seconds_to_send())):
            backend._set_message_as_failed(message)
            return False
        else:
            backend.publish_message(message)
            return True

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
        backend = self.get_backend(recipient)
        message = self.create_message(recipient, content, related_objects, tag, template, **kwargs)
        if not self.is_turned_on_batch_sending():
            backend.publish_message(message)
        return message

    def get_batch_max_seconds_to_send(self):
        """
        Return max timeout in seconds to send message
        """
        raise NotImplementedError

    def get_batch_size(self):
        """
        Return number of messages sent in batch
        """
        raise NotImplementedError

    def create_message(self, recipient, content, related_objects, tag, template,
                       priority=settings.DEFAULT_MESSAGE_PRIORITY, **kwargs):
        """
        Create message which will be logged in the database.
        :param recipient: email or phone number of the recipient
        :param content: content of the message
        :param related_objects: list of related objects that will be linked with the message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
        :param priority: priority of sending message 1 (highest) to 3 (lowest)
        :param kwargs: extra attributes that will be saved with the message
        """
        message = self.model.objects.create(
            recipient=recipient,
            content=content,
            tag=tag,
            template=template,
            template_slug=template.slug if template else None,
            priority=priority,
            **kwargs
        )
        if related_objects:
            message.related_objects.create_from_related_objects(*related_objects)
        return message

    def _get_backend_messages_map(self, messages):
        backends_messages_map = defaultdict(list)
        for message in messages:
            backend = self.get_backend(recipient=message.recipient)
            backends_messages_map[backend].append(message)
        return backends_messages_map

    def bulk_send_messages(self, messages):
        """
        Sends more messages together. If concrete backend provides send more messages at once the method
        can be overridden
        :param messages: list of messages
        """
        for backend, messages_for_backend in self._get_backend_messages_map(messages):
            backend.publish_messages(messages_for_backend)

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
        with transaction.atomic():
            messages = [
                self.create_message(recipient, content, related_objects, tag, template, **kwargs)
                for recipient in recipients
            ]
        self.bulk_send_messages(messages)
        return messages


class BaseBackend:

    config = AttrDict()

    def __init__(self, config=None):
        self.config = AttrDict({**self.config, **(config or {})})

    def _get_extra_sender_data(self):
        """
        Gets arguments that will be saved with the message in the extra_sender_data field
        """
        return {}

    def get_extra_message_kwargs(self):
        """
        Gets model message kwargs that will be saved with the message
        """
        return {}

    def _update_message(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message
        :param message: message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
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

    def _update_message_after_sending(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message after it was sent
        :param message: message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
        """
        self._update_message(
            message,
            extra_sender_data,
            number_of_send_attempts=message.number_of_send_attempts + 1,
            **kwargs
        )

    def _update_message_after_sending_error(self, message, extra_sender_data=None, state=None, **kwargs):
        """
        Method for updating state of the message after it was send with error result
        :param message: message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param state: error state of the message
        :param kwargs: changed object kwargs
        """

        number_of_send_attempts = message.number_of_send_attempts + 1

        if not state:
            state = (
                message.STATE.ERROR if (
                    number_of_send_attempts > self.get_batch_max_number_of_send_attempts()
                    or not self.get_retry_sending()
                ) else message.STATE.ERROR_RETRY
            )

        self._update_message(
            message,
            extra_sender_data,
            state=state,
            number_of_send_attempts=number_of_send_attempts,
            **kwargs
        )

    def _set_message_as_failed(self, message):
        """
        Method for updating state of the message to the final error state
        :param message: message object
        """
        self._update_message(
            message,
            state=message.STATE.ERROR,
        )

    def publish_message(self, message):
        """
        Send the message
        :param message: SMS message
        """
        raise NotImplementedError

    def publish_messages(self, messages):
        """
        Send bulk of messages at once
        :param messages: list of SMS message
        """
        return [self.publish_message(message) for message in sorted(messages, key=lambda m: m.priority)]

    def get_batch_max_number_of_send_attempts(self):
        """
        Return number attempts to send message
        """
        raise NotImplementedError

    def get_retry_sending(self):
        """
        Return True if message should be retried if sending fails
        """
        raise NotImplementedError


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


def send(recipient, content, related_objects=None, tag=None, message_controller=None, **kwargs):
    """
    Helper for sending message.
    :param recipient: email or phone number of the recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :param message_controller: controller sender instance
    :return: True if message was successfully sent or False if message is in error state
    """
    return message_controller.send(
        recipient,
        content,
        related_objects=related_objects,
        tag=tag,
        **kwargs
    ).failed
