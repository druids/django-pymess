import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.models import F, Q
from django.utils.timezone import now

from chamber.utils.transaction import atomic_with_signals

from pymess.config import get_email_sender, settings
from pymess.models import EmailMessage


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for pulling info of sent e-mails.
    """

    @atomic_with_signals
    def handle(self, *args, **options):
        email_sender = get_email_sender()

        delay = datetime.timedelta(seconds=settings.EMAIL_PULL_INFO_DELAY_SECONDS)
        messages = EmailMessage.objects.filter(
            # start_time = last_webhook_received_at + delay
            # info_changed_at < start_time
            # info_changed_at < last_webhook_received_at + delay
            Q(info_changed_at__isnull=True) | Q(info_changed_at__lt=F('last_webhook_received_at') + delay),
            last_webhook_received_at__lt=now() - delay,
            sent_at__gt=now() - datetime.timedelta(seconds=settings.EMAIL_PULL_INFO_MAX_TIMEOUT_FROM_SENT_SECONDS)
        ).order_by('-sent_at')
        self.stdout.write('Total number of emails to pull info: {}'.format(messages.count()))

        messages = messages[:settings.EMAIL_PULL_INFO_BATCH_SIZE]
        self.stdout.write('Number of emails in this batch: {}'.format(messages.count()))

        for message in messages:
            try:
                email_sender.pull_message_info(message)
            except Exception as ex:
                # Rollback should not be applied for already updated e-mails
                logger.exception(ex)
        self.stdout.write('DONE')
