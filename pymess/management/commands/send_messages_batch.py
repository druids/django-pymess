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

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--type', action='store', dest='type', default='input',
                            help='Tells Django what type of messages should be send '
                                 '(email/push-notification/dialer/sms).')

    def handle(self, type, *args, **options):
        sender = senders[type]()

        if not sender.is_turned_on_batch_sending():
            raise CommandError('Batch sending is turned off')

        sent = 0
        try:
            touched_message_pks = set()
            for _ in sender.get_batch_size():
                with atomic_with_signals:
                    message = sender.get_waiting_or_retry_messages().exclue(
                        pk__in=touched_message_pks
                    ).select_for_update(
                        nowait=True
                    ).order_by('created_at').first()
                    if not message:
                        break

                    touched_message_pks.add(message.pk)
                    try:
                        sender.publish_message(message)
                        sent += 1
                    except Exception as ex:
                        # Rollback should not be applied for already send e-mails
                        logger.exception(ex)

            self.stdout.write('{} messages sent'.format(sent))
        except DatabaseError:
            self.stdout.write('messages are already locked')

