import logging

from datetime import timedelta

from django.db import DatabaseError
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from pymess.config import get_email_sender, get_push_notification_sender, get_dialer_sender, get_sms_sender
from pymess.models import EmailMessage

from chamber.utils.transaction import atomic_with_signals


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for sending messages in batch.
    """

    senders = {
        'email': get_email_sender,
        'push-notification': get_push_notification_sender,
        'dialer': get_dialer_sender,
        'sms': get_sms_sender
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.touched_message_pks = set()
        self.send_message_pks = set()
        self.failed_message_pks = set()

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--type', action='store', dest='type', default='input',
                            help='Tells Django what type of messages should be send '
                                 '(email/push-notification/dialer/sms).')

    @atomic_with_signals
    def _send_message(self, sender):
        message = sender.get_waiting_or_retry_messages().exclude(
            pk__in=self.touched_message_pks
        ).select_for_update(
            nowait=True
        ).order_by('created_at').first()
        if not message:
            return

        self.touched_message_pks.add(message.pk)
        try:
            sender.publish_message(message)
            self.send_message_pks.add(message.pk)
        except Exception as ex:
            # Rollback should not be applied for already send e-mails
            logger.exception(ex)
            self.failed_message_pks.add(message.pk)

    def _print_result(self, title, message_pks):
        if message_pks:
            self.stdout.write('{}: {} ({})'.format(title, len(message_pks), ', '.join((str(pk) for pk in message_pks))))
        else:
            self.stdout.write('{}: {}'.format(title, len(message_pks)))

    def handle(self, type, *args, **options):
        sender = self.senders[type]()

        if not sender.is_turned_on_batch_sending():
            raise CommandError('Batch sending is turned off')

        try:
            for _ in range(sender.get_batch_size()):
                self._send_message(sender)
            self._print_result('sent messages', self.send_message_pks)
            self._print_result('failed messages', self.failed_message_pks)
        except DatabaseError:
            self.stdout.write('messages are already locked')

