import logging

from django.core.management.base import BaseCommand

from pymess.config import get_email_sender, settings
from pymess.models import EmailMessage

from chamber.utils.transaction import atomic_with_signals

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for pulling info of sent e-mails.
    """

    @atomic_with_signals
    def handle(self, *args, **options):
        email_sender = get_email_sender()

        messages = EmailMessage.objects.filter(require_pull_info=True).order_by('-sent_at')
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
