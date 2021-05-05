from datetime import datetime

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from pymess.models import EmailMessage


CHUNK_SIZE = 100


class Command(BaseCommand):
    """
    Command for migrating e-mail message contents from database to files.
    """

    def _get_qs(self):
        return EmailMessage.objects.filter(old_content__isnull=False)

    def handle(self, *args, **options):
        total_count = self._get_qs().count()
        count = 0

        while True:
            qs = self._get_qs()[:CHUNK_SIZE]
            if not qs.exists():
                self.stdout.write('Finished!')
                break

            for message in qs:
                assert bool(message.content_file) != bool(message.old_content)
                message.content_file.save(None, ContentFile(message.old_content.encode()))
                message.old_content = None
                message.save()

            count += qs.count()
            self.stdout.write('{}: Processed {} out of {} e-mails'.format(datetime.now(), count, total_count))
