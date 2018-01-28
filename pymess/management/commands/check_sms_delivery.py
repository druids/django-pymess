from django.core.management.base import BaseCommand

from pymess.config import get_sms_sender


class Command(BaseCommand):
    """
    Command for checking SMS delivery. SMS backend must support it.
    """

    def handle(self, *args, **kwargs):
        get_sms_sender().bulk_check_sms_states()
