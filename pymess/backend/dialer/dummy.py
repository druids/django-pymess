from django.utils import timezone

from pymess.backend.dialer import DialerBackend
from pymess.models import DialerMessage


class DummyDialerBackend(DialerBackend):
    """
    Dummy dialer backend used for testing environments. Backend only logs messages to the database.
    """

    def publish_message(self, message):
        self._update_message_after_sending(message, state=DialerMessage.State.DEBUG, sent_at=timezone.now(),
                                           is_final_state=True)
