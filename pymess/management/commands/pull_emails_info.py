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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.touched_message_pks = set()
        self.updated_messages = set()

    def _get_messages_queryset_to_update(self):
        delay = datetime.timedelta(seconds=settings.EMAIL_PULL_INFO_DELAY_SECONDS)
        return EmailMessage.objects.filter(
            # start_time = last_webhook_received_at + delay
            # info_changed_at < start_time
            # info_changed_at < last_webhook_received_at + delay
            Q(info_changed_at__isnull=True) | Q(info_changed_at__lt=F('last_webhook_received_at') + delay),
            last_webhook_received_at__lt=now() - delay,
            sent_at__gt=now() - datetime.timedelta(seconds=settings.EMAIL_PULL_INFO_MAX_TIMEOUT_FROM_SENT_SECONDS)
        ).order_by('-sent_at')

    @atomic_with_signals
    def _pull_message_info(self, email_sender):
        message = self._get_messages_queryset_to_update().exclude(
            pk__in=self.touched_message_pks
        ).select_for_update().first()

        if not message:
            return False

        self.touched_message_pks.add(message.pk)
        email_sender.pull_message_info(message)
        self.updated_messages.add(message.pk)
        return True

    def _print_result(self, title, message_pks):
        if message_pks:
            self.stdout.write('{}: {} ({})'.format(title, len(message_pks), ', '.join((str(pk) for pk in message_pks))))
        else:
            self.stdout.write('{}: {}'.format(title, len(message_pks)))

    def handle(self, *args, **options):
        email_sender = get_email_sender()

        for _ in range(settings.EMAIL_PULL_INFO_BATCH_SIZE):
            try:
                if not self._pull_message_info(email_sender):
                    break
            except Exception as ex:
                # One message error should not stop the whole cycle
                logger.exception(ex)

        self._print_result('updated messages', self.updated_messages)
        self._print_result('failed messages', self.touched_message_pks - self.updated_messages)
