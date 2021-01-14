from django.core.management.base import BaseCommand

from pymess.backend.dialer import DialerController


class Command(BaseCommand):
    """
    Command for checking dialer call status. Dialer backend must support it.
    """

    def handle(self, *args, **kwargs):
        DialerController().bulk_check_dialer_status()
