import logging

from django.utils.encoding import force_text

from chamber.exceptions import PersistenceException

from pymess.config import get_email_template_model, get_email_sender, settings
from pymess.models import EmailMessage
from pymess.utils import fullname
from pymess.lockfile import FileLock, AlreadyLocked, LockTimeout


LOGGER = logging.getLogger(__name__)


class EmailBackend(object):
    """
    Base class for E-mail backend containing implementation of e-mail service that
    is used for sending messages.
    """

    class EmailSendingError(Exception):
        pass

    def _get_extra_sender_data(self):
        """
        Gets arguments that will be saved with the message in the extra_sender_data field.
        """
        return {}

    def _get_extra_message_kwargs(self):
        """
        Gets model message kwargs that will be saved with the message.
        """
        return {}

    def update_message(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message after sending
        :param message: e-mail message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
        :return:
        """
        extra_sender_data = {
            **self._get_extra_sender_data(),
            **({} if extra_sender_data is None else extra_sender_data)
        }
        message.change_and_save(
            backend=fullname(self),
            extra_sender_data=extra_sender_data,
            **kwargs
        )

    def create_message(self, sender, sender_name, recipient, subject, content, related_objects, tag, template,
                       attachments, **email_kwargs):
        """
        Create e-mail which will be logged in the database.
        :param sender: e-mail address of the sender
        :param sender_name: friendly name of the sender
        :param recipient: e-mail address of the receiver
        :param subject: subject of the e-mail message
        :param content: content of the e-mail message
        :param related_objects: list of related objects that will be linked with the e-mail message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content, subject and sender of the message was created
        :param attachments: list of files that will be sent with the message as attachments
        :param email_kwargs: extra data that will be saved in JSON format in the extra_data model field
        """
        try:
            message = EmailMessage.objects.create(
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                content=content,
                subject=subject,
                state=self.get_initial_email_state(recipient),
                extra_data=email_kwargs,
                tag=tag,
                template=template,
                template_slug=template.slug if template else None,
                **self._get_extra_message_kwargs()
            )
            if related_objects:
                message.related_objects.create_from_related_objects(*related_objects)
            if attachments:
                message.attachments.create_from_tripples(*attachments)
            return message
        except PersistenceException as ex:
            raise self.EmailSendingError(force_text(ex))

    def publish_message(self, message):
        """
        Place for implementation logic of sending e-mail message.
        :param message: SMS message instance
        """
        raise NotImplementedError

    def send(self, sender, recipient, subject, content, sender_name=None, related_objects=None, tag=None,
             template=None, attachments=None, **email_kwargs):
        """
        Send e-mail with defined values
        :param sender: e-mail address of the sender
        :param recipient: e-mail address of the receiver
        :param subject: subject of the e-mail message
        :param content: content of the e-mail message
        :param sender_name: friendly name of the sender
        :param related_objects: list of related objects that will be linked with the e-mail message with generic
            relation
        :param tag: string mark that will be saved with the message
        :param template: template object from which content, subject and sender was created
        :param attachments: list of files that will be sent with the message as attachments
        :param email_kwargs: extra data that will be saved in JSON format in the extra_data model field
        """
        message = self.create_message(
            sender, sender_name, recipient, subject, content, related_objects, tag, template, attachments, **email_kwargs
        )
        if not settings.EMAIL_BATCH_SENDING:
            self.publish_message(message)
        return message

    def get_initial_email_state(self, recipient):
        """
        returns initial state for logged e-mail message.
        :param recipient: e-mail address of the recipient
        """
        return EmailMessage.STATE.WAITING

    def send_batch(self):
        """
        Method for sending e-mails in a batch mode.
        """
        if not settings.EMAIL_BATCH_SENDING:
            raise self.EmailSendingError('Batch sending is turned off')

        lock = FileLock(settings.EMAIL_BATCH_LOCK_FILE)
        try:
            lock.acquire(settings.EMAIL_BATCH_LOCK_WAIT_TIMEOUT)
        except AlreadyLocked:
            logging.debug("lock already in place. quitting.")
            return
        except LockTimeout:
            logging.debug("waiting for the lock timed out. quitting.")
            return

        sent = 0

        try:
            waiting_emails_qs = EmailMessage.objects.filter(
                state=EmailMessage.STATE.WAITING
            ).order_by('created_at')[:settings.EMAIL_BATCH_SIZE]
            for message in waiting_emails_qs:
                self.publish_message(message)
                sent += 1
        finally:
            logging.debug("releasing lock...")
            lock.release()
            logging.debug("released.")

        logging.info("{} e-mail sent".format(sent))


def send_template(recipient, slug, context_data, related_objects=None, attachments=None, tag=None):
    """
    Helper for building and sending e-mail message from a template.
    :param recipient: e-mail address of the receiver
    :param slug: slug of the e-mail template
    :param context_data: dict of data that will be sent to the template renderer
    :param related_objects: list of related objects that will be linked with the e-mail message with generic
        relation
    :param attachments: list of files that will be sent with the message as attachments
    :param tag: string mark that will be saved with the message 
    :return: e-mail message object or None if template cannot be sent
    """
    return get_email_template_model().objects.get(slug=slug).send(
        recipient,
        context_data,
        related_objects=related_objects,
        attachments=attachments,
        tag=tag
    )


def send(sender, recipient, subject, content, sender_name=None, related_objects=None, attachments=None, tag=None,
         **email_kwargs):
    """
    Helper for sending e-mail message.
    :param sender: e-mail address of the sender
    :param recipient: e-mail address of the receiver
    :param subject: subject of the e-mail message
    :param content: content of the e-mail message
    :param sender_name: friendly name of the sender
    :param related_objects: list of related objects that will be linked with the e-mail message with generic
        relation
    :param tag: string mark that will be saved with the message
    :param attachments: list of files that will be sent with the message as attachments
    :param email_kwargs: extra data that will be saved in JSON format in the extra_data model field
    :return: True if e-mail was successfully sent or False if e-mail is in error state
    """
    return get_email_sender().send(
        sender,
        recipient,
        subject,
        content,
        sender_name=sender_name,
        related_objects=related_objects,
        tag=tag,
        attachments=attachments,
        **email_kwargs
    ).failed