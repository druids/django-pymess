from functools import reduce

from operator import or_ as OR

from chamber.models import SmartModel
from chamber.utils.datastructures import ChoicesNumEnum
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager, Q
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from django.utils.translation import ugettext_lazy as _

from jsonfield.fields import JSONField

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

    def _get_related_object_pks(self, *related_objects):
        return [related_object.pk for related_object in related_objects]

    def _get_related_objects_qs_kwargs(self, *related_objects):
        return reduce(OR, (
            Q(**{
                'object_id': obj.pk,
                'content_type': ContentType.objects.get_for_model(obj)
            }) for obj in related_objects
        ))

    def update_related_objects(self, *related_objects, limit_to_model=None):
        delete_qs = self.all()
        if limit_to_model is not None:
            delete_qs = delete_qs.filter(content_type=ContentType.objects.get_for_model(limit_to_model))
        if related_objects:
            delete_qs = delete_qs.exclude(self._get_related_objects_qs_kwargs(*related_objects))
        delete_qs.delete()
        return self.get_or_create_from_related_objects(*related_objects)

    def get_or_create_from_related_object(self, related_object):
        return self.get_or_create(
            object_id_int=related_object.pk if has_int_pk(related_object) else None,
            object_id=related_object.pk,
            content_type=ContentType.objects.get_for_model(related_object)
        )

    def get_or_create_from_related_objects(self, *related_objects):
        return [
            self.get_or_create_from_related_object(related_object)
            for related_object in related_objects
        ]

    def get_related_objects_by_model(self, model):
        values_list_pk = 'object_id_int' if has_int_pk(model) else 'object_id'
        pks = self.filter(content_type=ContentType.objects.get_for_model(model)).values_list(values_list_pk)
        return model.objects.filter(pk__in=pks)

    def filter_from_related_objects(self, *related_objects):
        if hasattr(self, 'instance'):
            template_filter = (Q(template=self.instance) | Q(template__isnull=True))
        else:
            template_filter = Q(template__isnull=True)

        return self.model.objects.filter(template_filter).filter(self._get_related_objects_qs_kwargs(*related_objects))


class BaseMessage(SmartModel):

    STATE = ChoicesNumEnum()

    sent_at = models.DateTimeField(verbose_name=_('sent at'), null=True, blank=True, editable=False)
    recipient = models.CharField(verbose_name=_('recipient'), null=False, blank=False, max_length=20)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.CharField(verbose_name=_('backend'), null=True, blank=True, editable=False, max_length=250)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)
    extra_data = JSONField(verbose_name=_('extra data'), null=True, blank=True, editable=False)
    extra_sender_data = JSONField(verbose_name=_('extra sender data'), null=True, blank=True, editable=False)
    tag = models.SlugField(verbose_name=_('tag'), null=True, blank=True, editable=False)

    def __str__(self):
        return self.recipient

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class BaseRelatedObject(SmartModel):

    content_type = models.ForeignKey(ContentType, verbose_name=_('content type of the related object'),
                                     null=False, blank=False, on_delete=models.CASCADE)
    object_id = models.TextField(verbose_name=_('ID of the related object'), null=False, blank=False)
    object_id_int = models.PositiveIntegerField(verbose_name=_('ID of the related object in int format'), null=True,
                                                blank=True, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = RelatedObjectManager()

    class Meta:
        abstract = True
        ordering = ('-created_at',)

    def __str__(self):
        return str(self.content_object)


class BaseAbstractTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, editable=False,
                            primary_key=True)
    body = models.TextField(verbose_name=_('message body'), null=True, blank=False)
    is_active = models.BooleanField(null=False, blank=False, default=True, verbose_name=_('is active'))

    def _update_context_data(self, context_data):
        return context_data

    def render_text_template(self, text, context_data):
        context_data = self._update_context_data(context_data)
        return Template(text).render(Context(context_data))

    def render_body(self, context_data):
        return self.render_text_template(self.get_body(), context_data)

    def clean_body(self, context_data=None):
        try:
            self.render_body(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(_('Error during template body rendering: "{}"').format(ex))

    def get_body(self):
        return self.body

    def can_send_for_object(self, related_objects):
        return (
            not hasattr(self, 'disallowed_objects')
            or related_objects is None
            or not self.disallowed_objects.filter_from_related_objects(*related_objects).exists()
        )

    def can_send(self, recipient, related_objects):
        return self.is_active and self.can_send_for_object(related_objects)

    def get_backend_sender(self):
        raise NotImplementedError

    def send(self, recipient, context_data, related_objects=None, tag=None, **kwargs):
        if self.can_send(recipient, related_objects):
            return self.get_backend_sender().send(
                recipient=recipient,
                content=self.render_body(context_data),
                related_objects=related_objects,
                tag=tag,
                template=self,
                **kwargs,
            )
        else:
            return None

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        ordering = ('-created_at',)
