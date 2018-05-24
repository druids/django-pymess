from jsonfield.fields import JSONField

import six

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.encoding import force_text
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist

from chamber.models import SmartModel
from chamber.utils import remove_accent
from chamber.utils.datastructures import ChoicesNumEnum

from pymess.config import settings, get_sms_sender
from pymess.utils import normalize_phone_number

from .common import RelatedObjectManager


__ALL__ = (
    'OutputSMSMessage',
    'OutputSMSRelatedObjects',
    'AbstractSMSTemplate',
    'AbstractEmailTemplate',
    'SMSTemplate',
)


class OutputSMSMessage(SmartModel):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('UNKNOWN', _('unknown'), 2),
        ('SENDING', _('sending'), 3),
        ('SENT', _('sent'), 4),
        ('ERROR', _('error'), 5),
        ('DEBUG', _('debug'), 6),
        ('DELIVERED', _('delivered'), 7),
    )

    sent_at = models.DateTimeField(verbose_name=_('sent at'), null=True, blank=True, editable=False)
    sender = models.CharField(verbose_name=_('sender'), null=True, blank=True, max_length=20)
    recipient = models.CharField(verbose_name=_('recipient'), null=False, blank=False, max_length=20)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False, max_length=700)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    template = models.ForeignKey(settings.SMS_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='output_sms_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.CharField(verbose_name=_('backend'), null=True, blank=True, editable=False, max_length=250)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)
    extra_data = JSONField(verbose_name=_('extra data'), null=True, blank=True, editable=False)
    extra_sender_data = JSONField(verbose_name=_('extra sender data'), null=True, blank=True, editable=False)
    tag = models.SlugField(verbose_name=_('tag'), null=True, blank=True, editable=False)

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    def clean_content(self):
        if not settings.SMS_USE_ACCENT:
            self.content = six.text_type(remove_accent(six.text_type(self.content)))

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    def __str__(self):
        return self.recipient

    class Meta:
        verbose_name = _('output SMS')
        verbose_name_plural = _('output SMS')
        ordering = ('-created_at',)


class OutputSMSRelatedObject(SmartModel):

    output_sms_message = models.ForeignKey(OutputSMSMessage, verbose_name=_('output SMS message'), null=False,
                                           blank=False, on_delete=models.CASCADE, related_name='related_objects')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type of the related object'),
                                     null=False, blank=False, on_delete=models.CASCADE)
    object_id = models.TextField(verbose_name=_('ID of the related object'), null=False, blank=False)
    object_id_int = models.PositiveIntegerField(verbose_name=_('ID of the related object in int format'), null=True,
                                                blank=True, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = RelatedObjectManager()

    class Meta:
        verbose_name = _('related object of a SMS message')
        verbose_name_plural = _('related objects of SMS messages')
        ordering = ('-created_at',)


class AbstractSMSTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, editable=False,
                            db_index=True)
    body = models.TextField(verbose_name=_('message body'), null=True, blank=False)

    def clean_body(self, context_data=None):
        try:
            self.render_body(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(ugettext('Error during template body rendering: "{}"').format(ex))

    def get_body(self):
        return self.body

    def _update_context_data(self, context_data):
        return context_data

    def render_body(self, context_data):
        context_data = self._update_context_data(context_data)
        return Template(self.get_body()).render(Context(context_data))

    def can_send(self, recipient, context_data):
        return True

    def send(self, recipient, context_data, related_objects=None, tag=None):
        if self.can_send(recipient,context_data):
            return get_sms_sender().send(
                recipient,
                self.render_body(context_data),
                template=self,
                related_objects=related_objects,
                tag=tag
            )
        else:
            return None

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        verbose_name = _('SMS template')
        verbose_name_plural = _('SMS templates')
        ordering = ('-created_at',)


class SMSTemplate(AbstractSMSTemplate):
    pass
