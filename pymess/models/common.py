from chamber.models import SmartModel
from chamber.utils.datastructures import ChoicesNumEnum
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager
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

    def can_send(self, recipient, context_data):
        return self.is_active

    def get_backend_sender(self):
        raise NotImplementedError

    def send(self, recipient, context_data, related_objects=None, tag=None, **kwargs):
        if self.can_send(recipient, context_data):
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
