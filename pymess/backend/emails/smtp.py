import os

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.encoding import force_text

from pymess.backend.emails import EmailBackend
from pymess.models import EmailMessage


class SMTPEmailBackend(EmailBackend):
    """
    E-mail backend implementing standard SMTP service
    """

    def publish_message(self, message):
        email_message = EmailMultiAlternatives(
            message.subject,
            ' ',
            message.friendly_sender,
            [message.recipient],
        )
        email_message.attach_alternative(message.content, 'text/html')
        for attachment in message.attachments.all():
            email_message.attach(
                os.path.basename(attachment.file.name),
                attachment.file.read().decode('utf-8'),
                attachment.content_type,
            )
        try:
            email_message.send()
            self.update_message_after_sending(message, state=EmailMessage.STATE.SENT, sent_at=timezone.now())
        except Exception as ex:
            self.update_message_after_sending(message, state=EmailMessage.STATE.ERROR_NOT_SENT, error=force_text(ex))
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
