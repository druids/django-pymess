from chamber.exceptions import PersistenceException

from pymess.backend import BaseBackend, send_template as _send_template, send as _send, BaseController
from pymess.config import (
    ControllerType, get_push_notification_template_model, is_turned_on_push_notification_batch_sending, settings
)
from pymess.models import PushNotificationMessage


class PushNotificationController(BaseController):
    """Controller class for push notifications delegating message to correct push notification backend"""

    model = PushNotificationMessage
    backend_type_name = ControllerType.PUSH_NOTIFICATION

    class PushNotificationSendingError(Exception):
        pass

    def get_batch_max_seconds_to_send(self):
        return settings.PUSH_NOTIFICATION_BATCH_MAX_SECONDS_TO_SEND

    def get_batch_size(self):
        return settings.PUSH_NOTIFICATION_BATCH_SIZE

    def is_turned_on_batch_sending(self):
        return is_turned_on_push_notification_batch_sending()

    def create_message(self, recipient, content, related_objects, tag, template,
                       priority=settings.DEFAULT_MESSAGE_PRIORITY, **kwargs):
        try:
            notification = super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                template=template,
                tag=tag,
                priority=priority,
                **kwargs
            )
            return notification
        except PersistenceException as ex:
            raise self.PushNotificationSendingError(str(ex))


class PushNotificationBackend(BaseBackend):

    def get_batch_max_number_of_send_attempts(self):
        return settings.PUSH_NOTIFICATION_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

    def get_retry_sending(self):
        return settings.PUSH_NOTIFICATION_RETRY_SENDING and is_turned_on_push_notification_batch_sending()


def send_template(recipient, slug, context_data, related_objects=None, tag=None, send_immediately=None):
    """
    Helper for building and sending push notification message from a template.
    :param recipient: push notification recipient
    :param slug: slug of a push notifiaction template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the push notification using generic
        relation
    :param tag: string mark that will be saved with the message
    :param send_immediately: publishes the message regardless of the `is_turned_on_batch_sending` result
    :return: Push notification message object or None if template cannot be sent
    """
    return _send_template(
        recipient=recipient,
        slug=slug,
        context_data=context_data,
        related_objects=related_objects,
        tag=tag,
        template_model=get_push_notification_template_model(),
        send_immediately=send_immediately
    )


def send(recipient, content, related_objects=None, tag=None, send_immediately=False, **kwargs):
    """
    Helper for sending push notification.
    :param recipient: push notification recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :param send_immediately: publishes the message regardless of the `is_turned_on_batch_sending` result
    :return: True if push notification was successfully sent or False if message is in error state
    """
    return _send(
        recipient=recipient,
        content=content,
        related_objects=related_objects,
        tag=tag,
        message_controller=PushNotificationController(),
        send_immediately=send_immediately,
        **kwargs
    )
