from django.db.models import Manager
from django.contrib.contenttypes.models import ContentType

from pymess.utils import has_int_pk


class RelatedObjectManager(Manager):

    def create_from_related_object(self, related_object):
        return self.create(
            object_id_int=related_object.pk if has_int_pk(related_object) else None,
            object_id=related_object.pk,
            content_type=ContentType.objects.get_for_model(related_object)
        )

    def create_from_related_objects(self, *related_objects):
        return [
            self.create_from_related_object(related_object)
            for related_object in related_objects
        ]
