import logging

from datetime import timedelta

from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from pymess.config import get_email_sender, settings
from pymess.lockfile import FileLock, AlreadyLocked, LockTimeout
from pymess.models import EmailMessage


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for sending e-mails in batch.
    """

    def handle(self, *args, **options):
        if not settings.EMAIL_BATCH_SENDING:
            raise CommandError('Batch sending is turned off')

        lock = FileLock(settings.EMAIL_BATCH_LOCK_FILE)
        try:
            self.stdout.write('acquiring lock...')
            lock.acquire(settings.EMAIL_BATCH_LOCK_WAIT_TIMEOUT)
        except AlreadyLocked:
            logger.error('Send emails batch: lock already in place.')
            raise CommandError('lock already in place. quitting.')
        except LockTimeout:
            logger.error('Send emails batch: waiting for the lock timed out.')
            raise CommandError('waiting for the lock timed out. quitting.')

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
            ).order_by('created_at')[:settings.EMAIL_BATCH_SIZE]
            for message in messages_to_send:
                email_sender.publish_message(message)
                sent += 1
            self.stdout.write('{} e-mails sent'.format(sent))
        finally:
            self.stdout.write('releasing lock...')
            lock.release()
            self.stdout.write('released.')
