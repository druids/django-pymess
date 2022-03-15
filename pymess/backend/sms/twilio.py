from enum import Enum

from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _l

from pymess.backend.sms import SMSBackend
from pymess.enums import OutputSMSMessageState

from twilio.rest import TwilioRestClient


class TwilioState(str, Enum):

    ACCEPTED = 'ACCEPTED'
    QUEUED = 'QUEUED'
    SENDING = 'SENDING'
    SENT = 'SENT'
    DELIVERED = 'DELIVERED'
    RECEIVED = 'RECEIVED'
    FAILED = 'FAILED'
    UNDELIVERED = 'UNDELIVERED'


class TwilioSMSBackend(SMSBackend):
    """
    SMS backend implementing twilio service https://www.twilio.com/
    """

    twilio_client = None

    STATES_MAPPING = {
        TwilioState.ACCEPTED: OutputSMSMessageState.SENT,
        TwilioState.QUEUED: OutputSMSMessageState.SENT,
        TwilioState.SENDING: OutputSMSMessageState.SENT,
        TwilioState.SENT: OutputSMSMessageState.SENT,
        TwilioState.DELIVERED: OutputSMSMessageState.DELIVERED,
        TwilioState.RECEIVED: OutputSMSMessageState.DELIVERED,
        TwilioState.FAILED: OutputSMSMessageState.ERROR_UPDATE,
        TwilioState.UNDELIVERED: OutputSMSMessageState.ERROR_UPDATE,
    }

    def _get_twilio_client(self):
        """
        Connect to the twilio service
        """
        if not self.twilio_client:
            self.twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        return self.twilio_client

    def publish_message(self, message):
        """
        Method uses twilio REST client for sending SMS message
        :param message: SMS message
        """
        client = self._get_twilio_client()
        try:
            result = client.messages.create(
                from_=settings.TWILIO_SENDER,
                to=str(message.recipient),
                body=message.content
            )
            self._update_message_after_sending(
                message,
                state=self.STATES_MAPPING[TwilioState(result.status.upper())],
                error=result.error_message if result.error_message else None,
                sent_at=timezone.now()
            )
        except Exception as ex:
            self._update_message_after_sending_error(
                message, error=str(ex)
            )
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
