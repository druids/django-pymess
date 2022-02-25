import logging
from datetime import timedelta

from chamber.exceptions import PersistenceException
from django.utils.timezone import now

from pymess.backend import BaseBackend, BaseController
from pymess.backend import send as _send
from pymess.backend import send_template as _send_template
from pymess.config import (
    ControllerType, get_dialer_template_model, get_supported_backend_paths, is_turned_on_dialer_batch_sending,
    settings
)
from pymess.models import DialerMessage


LOGGER = logging.getLogger(__name__)


class DialerController(BaseController):
    """Controller class for dialer delegating message to correct dialer backend"""

    model = DialerMessage
    backend_type_name = ControllerType.DIALER

    class DialerSendingError(Exception):
        pass

    def get_batch_size(self):
        return settings.DIALER_BATCH_SIZE

    def get_batch_max_seconds_to_send(self):
        return settings.DIALER_BATCH_MAX_SECONDS_TO_SEND

    def get_initial_dialer_state(self, recipient):
        """
        returns initial state for logged dialer instance.
        :param recipient: phone number of the recipient
        """
        return self.model.State.WAITING

    def create_message(self, recipient, content=None, related_objects=None, tag=None, template=None, is_autodialer=True,
                       priority=settings.DEFAULT_MESSAGE_PRIORITY, **kwargs):
        """
        Create dialer message which will be logged in the database (content is not needed for this).
        :param recipient: phone number of the recipient
        :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
        :param is_autodialer: True if it's a autodialer call otherwise False
        :param priority: priority of sending message 1 (highest) to 3 (lowest)
        :param kwargs: extra attributes that will be saved with the message
        """
        extra_data = kwargs.pop('extra_data', {})
        try:
            return super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                tag=tag,
                template=template,
                state=self.get_initial_dialer_state(recipient),
                is_autodialer=is_autodialer,
                priority=priority,
                extra_data=kwargs,
                **self.get_backend(recipient).get_extra_message_kwargs(),
            )
        except PersistenceException as ex:
            raise self.DialerSendingError(str(ex))

    def bulk_check_dialer_status(self):
        """
        Method that finds messages that are not in the final state which were not sent and updates their states.
        """
        messages_to_check = self.model.objects.filter(
            is_final_state=False,
            sent_at__isnull=False,
            backend__in=get_supported_backend_paths(self.backend_type_name),
            created_at__gte=now() - timedelta(minutes=settings.DIALER_IDLE_MESSAGES_TIMEOUT_MINUTES),
        )
        if messages_to_check.exists():
            for backend, messages_for_backend in self._get_backend_messages_map(messages_to_check).items():
                backend._update_dialer_states(messages_for_backend)

    def is_turned_on_batch_sending(self):
        return is_turned_on_dialer_batch_sending()


class DialerBackend(BaseBackend):
    """
    Base class for dialer backend containing implementation of concrete dialer service that
    is used for automatic call to selected phone number.
    """

    def get_batch_max_number_of_send_attempts(self):
        return settings.DIALER_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

    def get_retry_sending(self):
        return settings.DIALER_RETRY_SENDING and is_turned_on_dialer_batch_sending()

    def _update_dialer_states(self, messages):
        """
        If dialer sender provides check dialer delivery this method can be overridden.
        :param messages: messages which state will be updated
        """
        raise NotImplementedError('Check dialer state is not supported with the backend')


def send_template(recipient, slug, context_data, related_objects=None, tag=None, send_immediately=False):
    """
    Helper for building and sending dialer message from a template.
    :param recipient: phone number of the recipient
    :param slug: slug of a dialer template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
    :param tag: string mark that will be saved with the message
    :param send_immediately: publishes the message regardless of the `is_turned_on_batch_sending` result
    :return: dialer message object or None if template cannot be sent
    """
    return _send_template(
        recipient,
        slug,
        context_data,
        related_objects,
        tag,
        template_model=get_dialer_template_model(),
        send_immediately=send_immediately
    )


def send(recipient, content, related_objects=None, tag=None, send_immediately=False, **kwargs):
    """
    Helper for sending dialer message.
    :param recipient: phone number of the recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :param send_immediately: publishes the message regardless of the `is_turned_on_batch_sending` result
    :return: True if dialer was successfully sent or False if message is in error state
    """
    return _send(
        recipient,
        content,
        related_objects,
        tag,
        message_controller=DialerController(),
        send_immediately=send_immediately,
        **kwargs
    )
