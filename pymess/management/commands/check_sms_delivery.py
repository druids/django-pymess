from django.core.management.base import BaseCommand

from pymess.backend.sms import SMSController


class Command(BaseCommand):
    """
    Command for checking SMS delivery. SMS backend must support it.
    """

    def handle(self, *args, **kwargs):
        SMSController().bulk_check_sms_states()
