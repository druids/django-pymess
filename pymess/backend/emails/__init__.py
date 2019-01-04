from django.utils.encoding import force_text

from chamber.exceptions import PersistenceException

from pymess.backend import BaseBackend, send_template as _send_template, send as _send
from pymess.config import get_email_template_model, get_email_sender, settings
from pymess.models import EmailMessage


class EmailBackend(BaseBackend):
    """
    Base class for E-mail backend containing implementation of e-mail service that
    is used for sending messages.
    """

    model = EmailMessage

    class EmailSendingError(Exception):
        pass

    def update_message(self, message, extra_sender_data=None, **kwargs):
        """
        Method for updating state of the message after sending
        :param message: e-mail message object
        :param extra_sender_data: extra data that will be saved to the extra_sender_data field
        :param kwargs: changed object kwargs
        :return:
        """
        super().update_message(
            message,
            extra_sender_data=extra_sender_data,
            number_of_send_attempts=message.number_of_send_attempts + 1,
            **kwargs
        )

    def create_message(self, sender, sender_name, recipient, subject, content, related_objects, tag, template,
                       attachments, **kwargs):
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
        :param kwargs: extra data that will be saved in JSON format in the extra_data model field
        """
        try:
            message = super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                tag=tag,
                template=template,
                sender=sender,
                sender_name=sender_name,
                subject=subject,
                state=self.get_initial_email_state(recipient),
                extra_data=kwargs,
                **self._get_extra_message_kwargs()
            )
            if attachments:
                message.attachments.create_from_tripples(*attachments)
            return message
        except PersistenceException as ex:
            raise self.EmailSendingError(force_text(ex))

    def send(self, sender, recipient, subject, content, sender_name=None, related_objects=None, tag=None,
             template=None, attachments=None, **kwargs):
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
        :param kwargs: extra data that will be saved in JSON format in the extra_data model field
        """
        message = self.create_message(
            sender, sender_name, recipient, subject, content, related_objects, tag, template, attachments, **kwargs
        )
        if not settings.EMAIL_BATCH_SENDING:
            self.publish_message(message)
        return message

    def get_initial_email_state(self, recipient):
        """
        returns initial state for logged e-mail message.
        :param recipient: e-mail address of the recipient
        """
        return self.model.STATE.WAITING


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
    return _send_template(
        recipient=recipient,
        slug=slug,
        context_data=context_data,
        related_objects=related_objects,
        tag=tag,
        template_model=get_email_template_model(),
        attachments=attachments,
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
        sender=sender,
        recipient=recipient,
        subject=subject,
        content=content,
        sender_name=sender_name,
        related_objects=related_objects,
        tag=tag,
        attachments=attachments,
        **email_kwargs
    ).failed
