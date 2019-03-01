from chamber.exceptions import PersistenceException
from django.utils.encoding import force_text

from pymess.backend import BaseBackend
from pymess.models import PushNotificationMessage


class PushNotificationBackend(BaseBackend):
    """Base class for push notification backend with implementation of push notification service used for sending."""

    model = PushNotificationMessage

    class PushNotificationSendingError(Exception):
        pass

    def create_message(self, recipient, content, related_objects, tag, template, **kwargs):
        try:
            notification = super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                template=template,
                tag=tag,
                **kwargs
            )
            return notification
        except PersistenceException as ex:
            raise self.PushNotificationSendingError(force_text(ex))
