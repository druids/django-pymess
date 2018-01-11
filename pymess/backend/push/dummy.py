from chamber.shortcuts import change_and_save

from pymess.backend.push import PushBackend
from pymess.models import AbstractPushNotification


class DummyPushBackend(PushBackend):
    """
    Dummy push notification backend used for testing environments. Backend only logs messages to the database.
    """

    name = 'dummy'

    def _publish_message(self, message):
        change_and_save(message, state=AbstractPushNotification.STATE.DEBUG)
