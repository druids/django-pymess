import logging

from datetime import timedelta

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext

from chamber.exceptions import PersistenceException

from pymess.config import settings, get_output_sms_model, get_sms_sender, get_sms_template_model
from pymess.models import AbstractOutputSMSMessage


LOGGER = logging.getLogger(__name__)


class SMSBackend(object):
    """
    Base class for SMS backend containing implementation of concrete SMS service that
    is used for sending SMS messages.
    """

    class SMSSendingError(Exception):
        pass

    @property
    def name(self):
        """
        Every backend must have defined unique name.
        """
        raise NotImplementedError

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

    def create_message(self, recipient, content, **sms_attrs):
        """
        Create SMS which will be logged in the database.
        :param recipient: phone number of the recipient
        :param content: content of the SMS message
        :param sms_attrs: extra attributes that will be saved with the message
        """
        try:
            return get_output_sms_model().objects.create(
                recipient=recipient,
                content=content,
                backend=self.name,
                state=self.get_initial_sms_state(recipient),
                extra_sender_data=self._get_extra_sender_data(),
                **sms_attrs,
                **self._get_extra_message_kwargs()
            )
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

    def send(self, recipient, content, **sms_attrs):
        """
        Send SMS with the text content to the phone number (recipient)
        :param recipient: phone number of the recipient
        :param content: text content of the message
        :param sms_attrs: extra attributes that will be stored to the message
        """
        message = self.create_message(recipient, content, **sms_attrs)
        self.publish_message(message)
        return message

    def bulk_send(self, recipients, content, **sms_attrs):
        """
        Send more SMS messages in one bulk
        :param recipients: list of phone numbers of recipients
        :param content: content of messages
        :param sms_attrs: extra attributes that will be stored with messages
        """
        messages = [self.create_message(recipient, content, **sms_attrs) for recipient in recipients]
        self.publish_messages(messages)
        return messages

    def get_initial_sms_state(self, recipient):
        """
        returns initial state for logged SMS instance.
        :param recipient: phone number of the recipient
        """
        return AbstractOutputSMSMessage.STATE.WAITING

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
        messages_to_check = get_output_sms_model().objects.filter(state=AbstractOutputSMSMessage.STATE.SENDING)
        if messages_to_check.exists():
            self._update_sms_states(messages_to_check)

        idle_output_sms = get_output_sms_model().objects.filter(
            state=AbstractOutputSMSMessage.STATE.SENDING,
            created_at__lt=timezone.now() - timedelta(minutes=settings.IDLE_MESSAGES_TIMEOUT_MINUTES)
        )
        if settings.LOG_IDLE_MESSAGES and idle_output_sms.exists():
            LOGGER.warning('{count_sms} Output SMS is more than {timeout} minutes in state "SENDING"'.format(
                count_sms=idle_output_sms.count(), timeout=settings.IDLE_MESSAGES_TIMEOUT_MINUTES
            ))

        if settings.SET_ERROR_TO_IDLE_MESSAGES:
            idle_output_sms.update(
                state=AbstractOutputSMSMessage.STATE.ERROR, error=ugettext('timeouted')
            )


def send_template(recipient, slug, context):
    return get_sms_template_model().objects.get(slug=slug).send(recipient, context)


def send(recipient, content, **sms_attrs):
    return self.get_sms_sender().send(recipient, content, **sms_attrs).failed