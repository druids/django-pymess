import codecs
import json
import os

from django.core import serializers
from django.core.management.base import BaseCommand

from pymess.config import get_email_template_model


class Command(BaseCommand):
    """
    Command dumps e-mails body to the HTML files inside directory. Every HTML file is named with e-mail slug.
    """

    def add_arguments(self, parser):
        parser.add_argument('--directory', dest='directory', type=str, required=True)
        parser.add_argument('--indent', default=0, dest='indent', type=int,
                            help='Specifies the indent level to use when pretty-printing output')

    def dump_template_model(self, directory, indent):
        print(directory)
        EmailTemplate = get_email_template_model()
        if EmailTemplate.objects.exists():
            emails_directory = os.path.join(directory)
            if not os.path.exists(emails_directory):
                os.makedirs(emails_directory)
            data = serializers.serialize('python', EmailTemplate.objects.all())
            for obj in data:
                with codecs.open(os.path.join(emails_directory, '{}.html'.format(obj['pk'])), 'w',
                                 encoding='utf-8-sig') as file:
                    file.write(obj['fields']['body'])
                    del obj['fields']['body']

            with codecs.open(os.path.join(emails_directory, 'data.json'), 'w') as file:
                file.write(json.dumps(data, cls=serializers.json.DjangoJSONEncoder, indent=indent))
            self.stdout.write('Stored: "{}" records'.format(len(data)))
        else:
            self.stdout.write('No records')

    def handle(self, *args, **options):
        indent = options.get('indent')
        directory = options.get('directory')
        self.stdout.write('Dumping e-mails')
        self.dump_template_model(directory, indent)
