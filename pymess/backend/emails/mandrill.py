import os
import base64

import requests
from attrdict import AttrDict

from json.decoder import JSONDecodeError

from django.utils import timezone
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

    config = AttrDict({
        'HEADERS': None,
        'TRACK_OPENS': False,
        'TRACK_CLICKS': False,
        'AUTO_TEXT': False,
        'INLINE_CSS': False,
        'URL_STRIP_QS': False,
        'PRESERVE_RECIPIENTS': False,
        'VIEW_CONTENT_LINK': True,
        'ASYNC': False,
        'TIMEOUT': 5,  # 5s
    })

    def _serialize_attachments(self, message):
        return [
            {
                'type': attachment.content_type,
                'name': os.path.basename(attachment.file.name),
                'content': base64.b64encode(attachment.file.read()).decode('utf-8')
            } for attachment in message.attachments.all()
        ]

    def _create_client(self, message):
        mandrill_client = mandrill.Mandrill(self.config.KEY)
        mandrill_client.session = generate_session(
            slug='pymess - Mandrill',
            related_objects=(message,),
            timeout=self.config.TIMEOUT
        )
        return mandrill_client

    def publish_message(self, message):
        mandrill_client = self._create_client(message)
        try:
            result = mandrill_client.messages.send(
                message={
                    'to': [{'email': message.recipient}],
                    'from_email': message.sender,
                    'from_name': message.sender_name,
                    'html': message.content,
                    'subject': message.subject,
                    'headers': self.config.HEADERS,
                    'track_opens': self.config.TRACK_OPENS,
                    'auto_text': self.config.AUTO_TEXT,
                    'inline_css': self.config.INLINE_CSS,
                    'url_strip_qs': self.config.URL_STRIP_QS,
                    'preserve_recipients': self.config.PRESERVE_RECIPIENTS,
                    'view_content_link': self.config.VIEW_CONTENT_LINK,
                    'async': self.config.ASYNC,
                    'attachments': self._serialize_attachments(message)
                },
            )[0]
            mandrill_state = result['status'].upper()
            state = self.MANDRILL_STATES_MAPPING.get(mandrill_state)
            error = (
                self.MANDRILL_STATES.get_label(mandrill_state) if state == EmailMessage.STATE.ERROR else None
            )
            if mandrill_state == self.MANDRILL_STATES.REJECTED:
                error += ', mandrill message: "{}"'.format(result['reject_reason'])

            extra_sender_data = message.extra_sender_data or {}
            extra_sender_data['result'] = result
            self._update_message_after_sending(
                message,
                state=state,
                sent_at=timezone.now(),
                extra_sender_data=extra_sender_data,
                error=error,
                external_id=result.get('_id')
            )
        except (mandrill.Error, JSONDecodeError, requests.exceptions.RequestException) as ex:
            self._update_message_after_sending_error(
                message,
                error=str(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (lost of information
            # about exception).

    def pull_message_info(self, message):
        if message.external_id:
            mandrill_client = self._create_client(message)
            try:
                info = mandrill_client.messages.info(message.external_id)
                self._update_message(
                    message,
                    extra_sender_data={**message.extra_sender_data, 'info': info},
                    info_changed_at=timezone.now(),
                    update_only_changed_fields=True,
                )
            except mandrill.UnknownMessageError:
                self._update_message(message, info_changed_at=timezone.now(), update_only_changed_fields=True)
        else:
            self._update_message(message, info_changed_at=timezone.now(), update_only_changed_fields=True)
