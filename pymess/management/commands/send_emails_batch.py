from django.core.management.base import BaseCommand

from pymess.config import get_email_sender


class Command(BaseCommand):
    """
    Command for sending e-mails in batch.
    """

    def handle(self, *args, **kwargs):
        get_email_sender().send_batch()
