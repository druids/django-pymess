from pymess import config
from pymess.models import AbstractPushNotification


class PushBackend(object):
    """
    Base class for push notification backend containing implementation of concrete push notification service that
    is used for sending messages.
    """

    @property
    def name(self):
        """
        Every backend must have defined unique name.
        """
        raise NotImplementedError

    def _create_push_notifications(self, user, content, **push_attrs):
        """
        Create new push notification object that will be send to the recipient
        :param user: application user object to which push notification will be send
        :param content: content of the push message
        :param push_attrs: extra attributes that will be saved with the message
        """
        return [
            config.get_push_notification_model().objects.create(
                user_device=user_device,
                content=content,
                state=AbstractPushNotification.STATE.WAITING,
                backend=self.name,
                **push_attrs
            )
            for user_device in user.user_devices.filter(is_active=True)
        ]

    def send(self, user, content, **push_attrs):
        """
        Send push notification with the text content to the user
        :param user: application user object to which push notification will be send
        :param content: text content of the message
        :param push_attrs: extra attributes that will be stored to the message
        """
        self._publish_message(self._create_push_notifications(user, content, **push_attrs))

    def bulk_send(self, users, content, **push_attrs):
        """
        Send more push notifications in one bulk
        :param users: list of application users object to which push notification will be send
        :param content: content of messages
        :param push_attrs: extra attributes that will be stored with messages
        """
        self._publish_messages([self._create_push_notifications(user, content, **push_attrs) for user in users])

    def _publish_message(self, message):
        """
        Place for implementation logic of sending push notifications.
        :param message: push notification message instance
        """
        raise NotImplementedError

    def _publish_messages(self, messages):
        """
        Sends more push notifications together. If concrete push notification backend provides send more messages
        at once the method can be overridden
        :param messages: list of push notification messages
        """
        [self._publish_message(message) for message in messages]