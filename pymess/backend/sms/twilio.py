from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _l

from chamber.utils.datastructures import ChoicesEnum

from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage

from twilio.rest import TwilioRestClient


class TwilioSMSBackend(SMSBackend):
    """
    SMS backend implementing twilio service https://www.twilio.com/
    """

    twilio_client = None

    STATE = ChoicesEnum(
        ('ACCEPTED', _l('accepted'), 'accepted'),
        ('QUEUED', _l('queued'), 'queued'),
        ('SENDING', _l('sending'), 'sending'),
        ('SENT', _l('sent'), 'sent'),
        ('DELIVERED', _l('delivered'), 'delivered'),  # TODO implement checking delivery status
        ('RECEIVED', _l('received'), 'received'),
        ('FAILED', _l('failed'), 'failed'),
        ('UNDELIVERED', _l('undelivered'), 'undelivered'),
    )

    STATES_MAPPING = {
        STATE.ACCEPTED: OutputSMSMessage.STATE.SENT,
        STATE.QUEUED: OutputSMSMessage.STATE.SENT,
        STATE.SENDING: OutputSMSMessage.STATE.SENT,
        STATE.SENT: OutputSMSMessage.STATE.SENT,
        STATE.DELIVERED: OutputSMSMessage.STATE.DELIVERED,
        STATE.RECEIVED: OutputSMSMessage.STATE.DELIVERED,
        STATE.FAILED: OutputSMSMessage.STATE.ERROR_UPDATE,
        STATE.UNDELIVERED: OutputSMSMessage.STATE.ERROR_UPDATE,
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
                to=force_text(message.recipient),
                body=message.content
            )
            self.update_message_after_sending(
                message,
                state=self.STATES_MAPPING[result.status],
                error=result.error_message if result.error_message else None,
                sent_at=timezone.now()
            )
        except Exception as ex:
            self.update_message_after_sending(
                message, state=OutputSMSMessage.STATE.ERROR_NOT_SENT, error=force_text(ex)
            )
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
