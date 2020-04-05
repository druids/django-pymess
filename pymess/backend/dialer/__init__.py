import logging
from datetime import timedelta

from chamber.exceptions import PersistenceException
from django.utils.encoding import force_text
from django.utils.timezone import now

from pymess.backend import BaseBackend
from pymess.backend import send as _send
from pymess.backend import send_template as _send_template
from pymess.config import get_dialer_sender, get_dialer_template_model, settings
from pymess.models import DialerMessage
from pymess.utils import fullname

LOGGER = logging.getLogger(__name__)


class DialerSendingError(Exception):
    pass


class DialerBackend(BaseBackend):
    """
    Base class for dialer backend containing implementation of concrete dialer service that
    is used for automatic call to selected phone number.
    """

    model = DialerMessage

    def is_turned_on_batch_sending(self):
        return settings.DIALER_BATCH_SENDING

    def get_batch_size(self):
        return settings.DIALER_BATCH_SIZE

    def get_batch_max_number_of_send_attempts(self):
        return settings.DIALER_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

    def get_batch_max_seconds_to_send(self):
        return settings.DIALER_BATCH_MAX_SECONDS_TO_SEND

    def get_retry_sending(self):
        return settings.DIALER_RETRY_SENDING and self.is_turned_on_batch_sending()

    def create_message(self, recipient, content, related_objects, tag, template, is_autodialer=True, **kwargs):
        """
        Create dialer message which will be logged in the database.
        :param recipient: phone number of the recipient
        :param content: content of the dialer message
        :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
        :param is_autodialer: True if it's a autodialer call otherwise False
        :param kwargs: extra attributes that will be saved with the message
        """
        try:
            return super().create_message(
                recipient,
                content,
                related_objects,
                tag,
                template,
                state=self.get_initial_dialer_state(recipient),
                is_autodialer=is_autodialer,
                extra_data=kwargs,
                **self._get_extra_message_kwargs()
            )
        except PersistenceException as ex:
            raise DialerSendingError(force_text(ex))

    def get_initial_dialer_state(self, recipient):
        """
        returns initial state for logged dialer instance.
        :param recipient: phone number of the recipient
        """
        return self.model.STATE.WAITING

    def _update_dialer_states(self, messages):
        """
        If dialer sender provides check dialer delivery this method can be overridden.
        :param messages: messages which state will be updated
        """
        raise NotImplementedError('Check dialer state is not supported with the backend')

    def bulk_check_dialer_status(self):
        """
        Method that finds messages that are not in the final state which were not sent and updates their states.
        """
        messages_to_check = self.model.objects.filter(
            is_final_state=False,
            sent_at__isnull=False,
            backend=fullname(self),
            created_at__gte=now() - timedelta(minutes=settings.DIALER_IDLE_MESSAGES_TIMEOUT_MINUTES),
        )
        if messages_to_check.exists():
            self._update_dialer_states(messages_to_check)


def send_template(recipient, slug, context_data, related_objects=None, tag=None):
    """
    Helper for building and sending dialer message from a template.
    :param recipient: phone number of the recipient
    :param slug: slug of a dialer template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
    :param tag: string mark that will be saved with the message
    :return: dialer message object or None if template cannot be sent
    """
    return _send_template(
        recipient,
        slug,
        context_data,
        related_objects,
        tag,
        template_model=get_dialer_template_model(),
    )


def send(recipient, content, related_objects=None, tag=None, **kwargs):
    """
    Helper for sending dialer message.
    :param recipient: phone number of the recipient
    :param content: text content of the messages
    :param related_objects:
    :param tag: string mark that will be saved with the message
    :param kwargs: extra attributes that will be stored with messages
    :return: True if dialer was successfully sent or False if message is in error state
    """
    return _send(
        recipient,
        content,
        related_objects,
        tag,
        message_sender=get_dialer_sender(),
        **kwargs
    )
