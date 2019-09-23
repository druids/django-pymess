import codecs
import os

from chamber.shortcuts import change_and_save

from pymess.config import settings


class SyncEmailTemplate:

    def __init__(self, template_slug):
        self.template_slug = template_slug

    def __call__(self, apps, schema_editor):
        directory = os.path.join(settings.EMAIL_HTML_DATA_DIRECTORY)

        with codecs.open(os.path.join(directory, '{}.html'.format(self.template_slug)), 'r',
                         encoding='utf-8-sig') as file:
            template_obj = apps.get_model(*settings.EMAIL_TEMPLATE_MODEL.split('.')).objects.get(
                slug=self.template_slug
            )
            change_and_save(template_obj, body=file.read())

