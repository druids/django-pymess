from chamber.exceptions import PersistenceException
from django.utils.encoding import force_text

from pymess.backend import BaseBackend, send_template as _send_template, send as _send
from pymess.config import settings, get_push_notification_template_model, get_push_notification_sender
from pymess.models import PushNotificationMessage


class PushNotificationBackend(BaseBackend):
    """Base class for push notification backend with implementation of push notification service used for sending."""

    model = PushNotificationMessage

    class PushNotificationSendingError(Exception):
        pass

    def is_turned_on_batch_sending(self):
        return settings.PUSH_NOTIFICATION_BATCH_SENDING

    def get_batch_size(self):
        return settings.PUSH_NOTIFICATION_BATCH_SIZE

    def get_batch_max_number_of_send_attempts(self):
        return settings.PUSH_NOTIFICATION_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

    def get_batch_max_seconds_to_send(self):
        return settings.PUSH_NOTIFICATION_BATCH_MAX_SECONDS_TO_SEND

    def get_retry_sending(self):
        return settings.PUSH_NOTIFICATION_RETRY_SENDING and self.is_turned_on_batch_sending()

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


def send_template(recipient, slug, context_data, related_objects=None, tag=None):
    """
    Helper for building and sending push notification message from a template.
    :param recipient: push notification recipient
    :param slug: slug of a push notifiaction template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the push notification using generic
        relation
    :param tag: string mark that will be saved with the message
    :return: Push notification message object or None if template cannot be sent
    """
    return _send_template(
        recipient=recipient,
        slug=slug,
        context_data=context_data,
        related_objects=related_objects,
        tag=tag,
        template_model=get_push_notification_template_model(),
    )


def send(recipient, content, related_objects=None, tag=None, **kwargs):
    """
    Helper for sending push notification.
    :param recipient: push notification recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :return: True if push notification was successfully sent or False if message is in error state
    """
    return _send(
        recipient=recipient,
        content=content,
        related_objects=related_objects,
        tag=tag,
        message_sender=get_push_notification_sender(),
        **kwargs
    )
