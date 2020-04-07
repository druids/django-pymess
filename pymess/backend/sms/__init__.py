import logging

from datetime import timedelta

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext

from chamber.exceptions import PersistenceException

from pymess.backend import BaseBackend, send_template as _send_template, send as _send
from pymess.config import settings, get_sms_template_model, get_sms_sender
from pymess.models import OutputSMSMessage
from pymess.utils import fullname


LOGGER = logging.getLogger(__name__)


class SMSBackend(BaseBackend):
    """
    Base class for SMS backend containing implementation of concrete SMS service that
    is used for sending SMS messages.
    """

    model = OutputSMSMessage

    class SMSSendingError(Exception):
        pass

    def is_turned_on_batch_sending(self):
        return settings.SMS_BATCH_SENDING

    def get_batch_size(self):
        return settings.SMS_BATCH_SIZE

    def get_batch_max_number_of_send_attempts(self):
        return settings.SMS_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

    def get_batch_max_seconds_to_send(self):
        return settings.SMS_BATCH_MAX_SECONDS_TO_SEND

    def get_retry_sending(self):
        return settings.SMS_RETRY_SENDING and self.is_turned_on_batch_sending()

    def create_message(self, recipient, content, related_objects, tag, template, **kwargs):
        """
        Create SMS which will be logged in the database.
        :param recipient: phone number of the recipient
        :param content: content of the SMS message
        :param related_objects: list of related objects that will be linked with the SMS message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
        :param kwargs: extra attributes that will be saved with the message
        """
        try:
            return super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                tag=tag,
                template=template,
                state=self.get_initial_sms_state(recipient),
                extra_data=kwargs,
                **self._get_extra_message_kwargs()
            )
        except PersistenceException as ex:
            raise self.SMSSendingError(force_text(ex))

    def get_initial_sms_state(self, recipient):
        """
        returns initial state for logged SMS instance.
        :param recipient: phone number of the recipient
        """
        return self.model.STATE.WAITING

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
        messages_to_check = self.model.objects.filter(state=self.model.STATE.SENDING)
        if messages_to_check.exists():
            self._update_sms_states(messages_to_check)

        idle_output_sms = self.model.objects.filter(
            state=self.model.STATE.SENDING,
            created_at__lt=timezone.now() - timedelta(minutes=settings.SMS_IDLE_MESSAGES_TIMEOUT_MINUTES),
            backend=fullname(self)
        )
        if settings.SMS_LOG_IDLE_MESSAGES and idle_output_sms.exists():
            LOGGER.warning('{count_sms} Output SMS is more than {timeout} minutes in state "SENDING"'.format(
                count_sms=idle_output_sms.count(), timeout=settings.SMS_IDLE_MESSAGES_TIMEOUT_MINUTES
            ))

        if settings.SMS_SET_ERROR_TO_IDLE_MESSAGES:
            idle_output_sms.update(
                state=self.model.STATE.ERROR_NOT_SENT, error=ugettext('timeouted')
            )


def send_template(recipient, slug, context_data, related_objects=None, tag=None):
    """
    Helper for building and sending SMS message from a template.
    :param recipient: phone number of the recipient
    :param slug: slug of a SMS template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the SMS message using generic
        relation
    :param tag: string mark that will be saved with the message
    :return: SMS message object or None if template cannot be sent
    """
    return _send_template(
        recipient=recipient,
        slug=slug,
        context_data=context_data,
        related_objects=related_objects,
        tag=tag,
        template_model=get_sms_template_model(),
    )


def send(recipient, content, related_objects=None, tag=None, **kwargs):
    """
    Helper for sending SMS message.
    :param recipient: phone number of the recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :return: True if SMS was successfully sent or False if message is in error state
    """
    return _send(
        recipient=recipient,
        content=content,
        related_objects=related_objects,
        tag=tag,
        message_sender=get_sms_sender(),
        **kwargs
    )
