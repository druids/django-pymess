from pymess.backend.push import PushNotificationBackend
from pymess.models import PushNotificationMessage


class DummyPushNotificationBackend(PushNotificationBackend):
    """Dummy push notification backend used for testing environments. Backend only logs messages to the database."""

    def publish_message(self, message):
        self.update_message_after_sending(message, state=PushNotificationMessage.STATE.DEBUG)
