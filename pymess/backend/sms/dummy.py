from django.utils import timezone
from pymess.backend.sms import SMSBackend


class DummySMSBackend(SMSBackend):
    """
    Dummy SMS backend used for testing environments. Backend only logs messages to the database.
    """

    def publish_message(self, message):
        self._update_message_after_sending(message, state=message.State.DEBUG, sent_at=timezone.now())
