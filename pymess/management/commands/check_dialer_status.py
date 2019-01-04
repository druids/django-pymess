from django.core.management.base import BaseCommand

from pymess.config import get_dialer_sender


class Command(BaseCommand):
    """
    Command for checking dialer call status. Dialer backend must support it.
    """

    def handle(self, *args, **kwargs):
        get_dialer_sender().bulk_check_dialer_status()
