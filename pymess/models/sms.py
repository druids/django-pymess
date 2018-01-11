import six
from phonenumber_field.modelfields import PhoneNumberField

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.template import Template, Context

from chamber.models import SmartModel
from chamber.shortcuts import get_object_or_none
from chamber.utils import remove_accent
from chamber.utils.datastructures import ChoicesNumEnum

from pymess.config import settings, get_sms_template_model, get_sms_sender


@python_2_unicode_compatible
class AbstractOutputSMSMessage(SmartModel):

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
    sender = PhoneNumberField(verbose_name=_('sender'), null=True, blank=True, editable=False)
    recipient = PhoneNumberField(verbose_name=_('recipient'), null=False, blank=False)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False, max_length=700)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.SlugField(verbose_name=_('backend'), null=False, blank=False, editable=False)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)

    def template(self):
        return get_object_or_none(get_sms_template_model(), slug=self.template_slug) or self.template_slug
    template.short_description = _('template')

    def clean_content(self):
        if not settings.USE_ACCENT:
            self.content = six.text_type(remove_accent(six.text_type(self.content)))

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    def __str__(self):
        return str(self.recipient)

    class Meta:
        abstract = True
        verbose_name = _('output SMS')
        verbose_name_plural = _('output SMS')
        ordering = ('-created_at',)


@python_2_unicode_compatible
class AbstractSMSTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, editable=False)
    body = models.TextField(verbose_name=_('message body'), null=True, blank=False)

    def render(self, phone, context):
        return Template(self.body).render(Context(context))

    def send(self, phone, context):
        get_sms_sender().send(phone, self.render(phone, context))

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        verbose_name = _('SMS template')
        verbose_name_plural = _('SMS templates')
