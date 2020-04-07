from chamber.shortcuts import change_and_save

from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage


class DummySMSBackend(SMSBackend):
    """
    Dummy SMS backend used for testing environments. Backend only logs messages to the database.
    """

    def publish_message(self, message):
        self.update_message_after_sending(message, state=OutputSMSMessage.STATE.DEBUG)
