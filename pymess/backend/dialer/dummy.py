from pymess.backend.dialer import DialerBackend
from pymess.models import DialerMessage


class DummyDialerBackend(DialerBackend):
    """
    Dummy dialer backend used for testing environments. Backend only logs messages to the database.
    """

    def _update_dialer_states(self, messages):
        pass

    def publish_message(self, message):
        self.update_message(message, state=DialerMessage.STATE.DEBUG)
