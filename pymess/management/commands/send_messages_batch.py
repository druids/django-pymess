import logging

from chamber.utils.transaction import atomic_with_signals
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from pymess.backend.dialer import DialerController
from pymess.backend.emails import EmailController
from pymess.backend.push import PushNotificationController
from pymess.backend.sms import SMSController

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for sending messages in batch.
    """

    controllers = {
        'email': EmailController(),
        'push-notification': PushNotificationController(),
        'dialer': DialerController(),
        'sms': SMSController()
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.touched_message_pks = set()
        self.send_message_pks = set()
        self.failed_message_pks = set()

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--type', action='store', dest='type', default='email',
                            help='Tells Django what type of messages should be send '
                                 '(email/push-notification/dialer/sms).')

    @atomic_with_signals
    def _send_message(self, controller):
        message = controller.get_waiting_or_retry_messages().exclude(
            pk__in=self.touched_message_pks
        ).select_for_update(
            nowait=True
        ).order_by('priority', 'created_at').first()
        if not message or not controller.is_turned_on_batch_sending():
            return False

        self.touched_message_pks.add(message.pk)
        try:
            if controller.publish_or_retry_message(message):
                self.send_message_pks.add(message.pk)
            else:
                self.failed_message_pks.add(message.pk)
        except Exception as ex:
            # Rollback should not be applied for already send e-mails
            logger.exception(ex)
            self.failed_message_pks.add(message.pk)
        return True

    def _print_result(self, title, message_pks):
        if message_pks:
            self.stdout.write('{}: {} ({})'.format(title, len(message_pks), ', '.join((str(pk) for pk in message_pks))))
        else:
            self.stdout.write('{}: {}'.format(title, len(message_pks)))

    def handle(self, type, *args, **options):
        controller = self.controllers[type]
        if not controller.is_turned_on_batch_sending():
            raise CommandError('Batch sending is turned off')

        try:
            for _ in range(controller.get_batch_size()):
                if not self._send_message(controller):
                    break
            self._print_result('sent messages', self.send_message_pks)
            self._print_result('failed messages', self.failed_message_pks)
        except DatabaseError:
            self.stdout.write('messages are already locked')
