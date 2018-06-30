import codecs
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from pymess.config import get_email_template_model, settings


class Command(BaseCommand):
    """
    Command synchronize e-mails body from directory.
    Every e-mail body is named with e-mail slug and stored as a HTML file.
    """

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity'))
        if verbosity > 0:
            self.stdout.write('Syncing e-mails')

        directory = os.path.join(settings.EMAIL_HTML_DATA_DIRECTORY)
        files_with_email_html_body = [
            filename for filename in os.listdir(directory) if filename.endswith('.html')
        ]
        for filename in files_with_email_html_body:
            try:
                template_obj = get_email_template_model().objects.get(slug=filename[:-5])
                with codecs.open(os.path.join(directory, filename), 'r', encoding='utf-8-sig') as file:
                    template_obj.change_and_save(body=file.read())
            except ObjectDoesNotExist:
                if verbosity > 0:
                    self.stderr.write('Template model with slug "{}" does not exists'.format(filename[:-5]))
        if verbosity > 0:
            self.stdout.write(
                self.style.SUCCESS('Synced "{}" e-mail templates'.format(len(files_with_email_html_body)))
            )
