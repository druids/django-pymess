from jsonfield.fields import JSONField

import six
from phonenumber_field.modelfields import PhoneNumberField

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.template import Template, Context

from chamber.models import SmartModel
from chamber.shortcuts import get_object_or_none
from chamber.utils import remove_accent
from chamber.utils.datastructures import ChoicesNumEnum

from pymess.config import settings, get_sms_template_model, get_sms_sender
from pymess.utils import normalize_phone_number


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
    sender = models.CharField(verbose_name=_('sender'), null=True, blank=True, max_length=20)
    recipient = models.CharField(verbose_name=_('recipient'), null=False, blank=False, max_length=20)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False, max_length=700)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    template = models.ForeignKey(settings.SMS_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL)
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.SlugField(verbose_name=_('backend'), null=False, blank=False, editable=False)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)
    extra_sender_data = JSONField(verbose_name=_('extra sender data'), null=True, blank=True, editable=False)

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    def clean_content(self):
        if not settings.SMS_USE_ACCENT:
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

    def render(self, recipient, context):
        return Template(self.body).render(Context(context))

    def can_send(self, recipient, context):
        return True

    def send(self, recipient, context):
        if self.can_send(recipient,context):
            return get_sms_sender().send(
                recipient, self.render(recipient, context), template_slug=self.slug, template=self
            )
        else:
            return None

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        verbose_name = _('SMS template')
        verbose_name_plural = _('SMS templates')
