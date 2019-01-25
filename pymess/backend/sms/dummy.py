from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage


class DummySMSBackend(SMSBackend):
    """
    Dummy SMS backend used for testing environments. Backend only logs messages to the database.
    """

    def _update_sms_states(self, messages):
        pass

    def publish_message(self, message):
        self.update_message(message, state=OutputSMSMessage.STATE.DEBUG)
