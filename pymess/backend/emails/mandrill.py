import os
import base64

import requests

from json.decoder import JSONDecodeError

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from chamber.utils.datastructures import ChoicesEnum

import mandrill

from pymess.backend.emails import EmailBackend
from pymess.models import EmailMessage
from pymess.config import settings
from pymess.utils.logged_requests import generate_session


class MandrillEmailBackend(EmailBackend):
    """
    E-mail backend implementing Mandrill service (https://mandrillapp.com/api/docs/index.python.html).
    """

    MANDRILL_STATES = ChoicesEnum(
        ('SENT', _('sent')),
        ('QUEUED', _('queued')),
        ('SCHEDULED', _('scheduled')),
        ('REJECTED', _('rejected')),
        ('INVALID', _('invalid')),
    )

    MANDRILL_STATES_MAPPING = {
        MANDRILL_STATES.SENT: EmailMessage.STATE.SENT,
        MANDRILL_STATES.QUEUED: EmailMessage.STATE.SENT,
        MANDRILL_STATES.SCHEDULED: EmailMessage.STATE.SENT,
        MANDRILL_STATES.REJECTED: EmailMessage.STATE.ERROR,
        MANDRILL_STATES.INVALID: EmailMessage.STATE.ERROR,
    }

    def _serialize_attachments(self, message):
        return [
            {
                'type': attachment.content_type,
                'name': os.path.basename(attachment.file.name),
                'content': base64.b64encode(attachment.file.read()).decode('utf-8')
            } for attachment in message.attachments.all()
        ]

    def publish_message(self, message):
        mandrill_client = mandrill.Mandrill(settings.EMAIL_MANDRILL.KEY)
        mandrill_client.session = generate_session(
            slug='pymess - Mandrill',
            related_objects=(message,),
            timeout=settings.EMAIL_MANDRILL.TIMEOUT
        )
        try:
            result = mandrill_client.messages.send(
                message={
                    'to': [{'email': message.recipient}],
                    'from_email': message.sender,
                    'from_name': message.sender_name,
                    'html': message.content,
                    'subject': message.subject,
                    'headers': settings.EMAIL_MANDRILL.HEADERS,
                    'track_opens': settings.EMAIL_MANDRILL.TRACK_OPENS,
                    'auto_text': settings.EMAIL_MANDRILL.AUTO_TEXT,
                    'inline_css': settings.EMAIL_MANDRILL.INLINE_CSS,
                    'url_strip_qs': settings.EMAIL_MANDRILL.URL_STRIP_QS,
                    'preserve_recipients': settings.EMAIL_MANDRILL.PRESERVE_RECIPIENTS,
                    'view_content_link': settings.EMAIL_MANDRILL.VIEW_CONTENT_LINK,
                    'async': settings.EMAIL_MANDRILL.ASYNC,
                    'attachments': self._serialize_attachments(message)
                },
            )[0]
            mandrill_state = result['status'].upper()
            state = self.MANDRILL_STATES_MAPPING.get(mandrill_state)
            error = self.MANDRILL_STATES.get_label(mandrill_state) if state == EmailMessage.STATE.ERROR else None
            if mandrill_state == self.MANDRILL_STATES.REJECTED:
                error += ', mandrill message: "{}"'.format(result['reject_reason'])

            extra_sender_data = message.extra_sender_data or {}
            extra_sender_data['result'] = result
            self.update_message(message, state=state, sent_at=timezone.now(),
                                extra_sender_data=extra_sender_data, error=error)
        except (mandrill.Error, JSONDecodeError, requests.exceptions.RequestException) as ex:
            self.update_message(message, state=EmailMessage.STATE.ERROR, error=force_text(ex))
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (lost of information
            # about exception).
