from chamber.shortcuts import change_and_save

from pymess.backend.sms import SMSBackend
from pymess.models import AbstractOutputSMSMessage


class DummySMSBackend(SMSBackend):
    """
    Dummy SMS backend used for testing environments. Backend only logs messages to the database.
    """

    name = 'dummy'

    def publish_message(self, message):
        change_and_save(message, state=AbstractOutputSMSMessage.STATE.DEBUG)
