import logging
from datetime import timedelta

from django.utils.encoding import force_text
from django.utils.timezone import now

from chamber.exceptions import PersistenceException

from pymess.backend import BaseBackend, send_template as _send_template, send as _send
from pymess.config import settings, get_dialer_template_model, get_dialer_sender
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

    def create_message(self, recipient, content, related_objects, tag, template, **kwargs):
        """
        Create dialer message which will be logged in the database.
        :param recipient: phone number of the recipient
        :param content: content of the dialer message
        :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content of the message was created
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
        return self.model.STATE.READY

    def _update_dialer_states(self, messages):
        """
        If dialer sender provides check dialer delivery this method can be overridden.
        :param messages: messages which state will be updated
        """
        raise NotImplementedError('Check dialer state is not supported with the backend')

    def bulk_check_dialer_status(self):
        """
        Method that finds messages that are not in the final state and updates their states.
        """
        messages_to_check = self.model.objects.filter(
            is_final_state=False,
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
