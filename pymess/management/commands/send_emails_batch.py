import logging

from datetime import timedelta

from django.db import DatabaseError
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from pymess.config import get_email_sender, settings
from pymess.models import EmailMessage

from chamber.utils.transaction import atomic_with_signals


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for sending e-mails in batch.
    """

    @atomic_with_signals
    def handle(self, *args, **options):
        if not settings.EMAIL_BATCH_SENDING:
            raise CommandError('Batch sending is turned off')

        email_sender = get_email_sender()

        sent = 0
        try:
            messages_to_send = EmailMessage.objects.filter(
                Q(state=EmailMessage.STATE.WAITING) |
                Q(
                    state=EmailMessage.STATE.ERROR,
                    number_of_send_attempts__lte=settings.EMAIL_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS,
                    created_at__gte=now() - timedelta(seconds=settings.EMAIL_BATCH_MAX_SECONDS_TO_SEND)
                )
            ).select_for_update(nowait=True).order_by('created_at')[:settings.EMAIL_BATCH_SIZE]
            for message in messages_to_send:
                try:
                    email_sender.publish_message(message)
                    sent += 1
                except Exception as ex:
                    # Rollback shoud not be applied for already send e-mails
                    logger.exception(ex)
            self.stdout.write('{} e-mails sent'.format(sent))
        except DatabaseError:
            self.stdout.write('e-mail messages are already locked')

