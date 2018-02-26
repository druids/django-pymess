import logging

from datetime import timedelta

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext

from chamber.exceptions import PersistenceException

from pymess.config import settings, get_sms_template_model, get_sms_sender
from pymess.models import OutputSMSMessage
from pymess.utils import fullname


LOGGER = logging.getLogger(__name__)


class SMSBackend(object):
    """
    Base class for SMS backend containing implementation of concrete SMS service that
    is used for sending SMS messages.
    """

    class SMSSendingError(Exception):
        pass

    def _get_extra_sender_data(self):
        """
        Gets arguments that will be saved with the sms message in the extra_sender_data field
        """
        return {}

    def _get_extra_message_kwargs(self):
        """
        Gets model message kwargs that will be saved with the sms message
        """
        return {}

    def update_message(self, message, extra_sender_data=None, **kwargs):
        extra_sender_data = {
            **self._get_extra_sender_data(),
            **({} if extra_sender_data is None else extra_sender_data)
        }
        message.change_and_save(
            backend=fullname(self),
            extra_sender_data=extra_sender_data,
            **kwargs
        )

    def create_message(self, recipient, content, related_objects, tag, template, **sms_kwargs):
        """
        Create SMS which will be logged in the database.
        :param recipient: phone number of the recipient
        :param content: content of the SMS message
        :param sms_attrs: extra attributes that will be saved with the message
        """
        try:
            message = OutputSMSMessage.objects.create(
                recipient=recipient,
                content=content,
                state=self.get_initial_sms_state(recipient),
                extra_data=sms_kwargs,
                tag=tag,
                template=template,
                template_slug=template.slug if template else None,
                **self._get_extra_message_kwargs()
            )
            if related_objects:
                message.related_objects.create_from_related_objects(*related_objects)
            return message
        except PersistenceException as ex:
            raise self.SMSSendingError(force_text(ex))

    def publish_message(self, message):
        """
        Place for implementation logic of sending SMS message.
        :param message: SMS message instance
        """
        raise NotImplementedError

    def publish_messages(self, messages):
        """
        Sends more SMS messages together. If concrete SMS backend provides send more messages at once the method
        can be overridden
        :param messages: list of SMS messages
        """
        [self.publish_message(message) for message in messages]

    def send(self, recipient, content, related_objects=None, tag=None, template=None, **sms_kwargs):
        """
        Send SMS with the text content to the phone number (recipient)
        :param recipient: phone number of the recipient
        :param content: text content of the message
        :param sms_attrs: extra attributes that will be stored to the message
        """
        message = self.create_message(recipient, content, related_objects, tag, template, **sms_kwargs)
        self.publish_message(message)
        return message

    def bulk_send(self, recipients, content, related_objects=None, tag=None, template=None, **sms_attrs):
        """
        Send more SMS messages in one bulk
        :param recipients: list of phone numbers of recipients
        :param content: content of messages
        :param sms_attrs: extra attributes that will be stored with messages
        """
        messages = [
            self.create_message(recipient, content, related_objects, tag, template, **sms_attrs)
            for recipient in recipients
        ]
        self.publish_messages(messages)
        return messages

    def get_initial_sms_state(self, recipient):
        """
        returns initial state for logged SMS instance.
        :param recipient: phone number of the recipient
        """
        return OutputSMSMessage.STATE.WAITING

    def _update_sms_states(self, messages):
        """
        If SMS sender provides check SMS delivery this method can be overridden.
        :param messages: messages which state will be updated
        """
        raise NotImplementedError('Check SMS state is not supported with the backend')

    def bulk_check_sms_states(self):
        """
        Method that find messages that is not in the final state and updates its states.
        """
        messages_to_check = OutputSMSMessage.objects.filter(state=OutputSMSMessage.STATE.SENDING)
        if messages_to_check.exists():
            self._update_sms_states(messages_to_check)

        idle_output_sms = OutputSMSMessage.objects.filter(
            state=OutputSMSMessage.STATE.SENDING,
            created_at__lt=timezone.now() - timedelta(minutes=settings.SMS_IDLE_MESSAGES_TIMEOUT_MINUTES)
        )
        if settings.SMS_LOG_IDLE_MESSAGES and idle_output_sms.exists():
            LOGGER.warning('{count_sms} Output SMS is more than {timeout} minutes in state "SENDING"'.format(
                count_sms=idle_output_sms.count(), timeout=settings.SMS_IDLE_MESSAGES_TIMEOUT_MINUTES
            ))

        if settings.SMS_SET_ERROR_TO_IDLE_MESSAGES:
            idle_output_sms.update(
                state=OutputSMSMessage.STATE.ERROR, error=ugettext('timeouted')
            )


def send_template(recipient, slug, context_data, related_objects=None, tag=None):
    return get_sms_template_model().objects.get(slug=slug).send(
        recipient,
        context_data,
        related_objects=related_objects,
        tag=tag
    )


def send(recipient, content, related_objects=None, tag=None, **sms_attrs):
    return get_sms_sender().send(
        recipient,
        content,
        related_objects=related_objects,
        tag=tag,
        **sms_attrs
    ).failed