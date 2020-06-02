from chamber.utils import remove_accent
from chamber.utils.datastructures import ChoicesNumEnum
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from pymess.config import settings, get_sms_sender
from pymess.utils import normalize_phone_number

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject


__all__ = (
    'OutputSMSMessage',
    'OutputSMSRelatedObject',
    'AbstractSMSTemplate',
    'SMSTemplate',
    'SMSTemplateDisallowedObject',
)


class OutputSMSMessage(BaseMessage):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('UNKNOWN', _('unknown'), 2),
        ('SENDING', _('sending'), 3),
        ('SENT', _('sent'), 4),
        ('ERROR_UPDATE', _('error message update'), 5),
        ('DEBUG', _('debug'), 6),
        ('DELIVERED', _('delivered'), 7),
        ('ERROR_NOT_SENT', _('error message was not sent'), 8),
    )

    content = models.TextField(verbose_name=_('content'), null=False, blank=False, max_length=700)
    template = models.ForeignKey(settings.SMS_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='output_sms_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False,
                                db_index=True)
    sender = models.CharField(verbose_name=_('sender'), null=True, blank=True, max_length=20)

    class Meta(BaseMessage.Meta):
        verbose_name = _('output SMS')
        verbose_name_plural = _('output SMS')

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    def clean_content(self):
        if not settings.SMS_USE_ACCENT:
            self.content = str(remove_accent(str(self.content)))

    @property
    def failed(self):
        return self.state == self.STATE.ERROR_NOT_SENT


class OutputSMSRelatedObject(BaseRelatedObject):

    output_sms_message = models.ForeignKey(OutputSMSMessage, verbose_name=_('output SMS message'), null=False,
                                           blank=False, on_delete=models.CASCADE, related_name='related_objects')

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('related object of a SMS message')
        verbose_name_plural = _('related objects of SMS messages')


class AbstractSMSTemplate(BaseAbstractTemplate):

    def get_backend_sender(self):
        return get_sms_sender()

    class Meta(BaseAbstractTemplate.Meta):
        abstract = True
        verbose_name = _('SMS template')
        verbose_name_plural = _('SMS templates')


class SMSTemplate(AbstractSMSTemplate):
    pass


class SMSTemplateDisallowedObject(BaseRelatedObject):

    template = models.ForeignKey(
        verbose_name=_('template'),
        to=SMSTemplate,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='disallowed_objects',
        db_index=True
    )

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('disallowed object of an SMS template')
        verbose_name_plural = _('disallowed objects of SMS templates')
