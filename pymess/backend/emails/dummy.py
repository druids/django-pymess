from django.utils import timezone

from pymess.backend.emails import EmailBackend
from pymess.models import EmailMessage


class DummyEmailBackend(EmailBackend):
    """
    Dummy e-mail backend used for testing environments. Backend only logs messages to the database.
    """

    def publish_message(self, message):
        self._update_message_after_sending(message, state=EmailMessage.STATE.DEBUG, sent_at=timezone.now())

    def pull_message_info(self, message):
        self._update_message(
            message,
            extra_sender_data={**message.extra_sender_data, 'info': {'debug': True}},
            info_changed_at=timezone.now(),
            update_only_changed_fields=True,
        )
