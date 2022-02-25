from chamber.utils import remove_accent
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from pymess.config import settings
from pymess.utils import normalize_phone_number
from pymess.enums import OutputSMSMessageState

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject


__all__ = (
    'OutputSMSMessage',
    'OutputSMSRelatedObject',
    'AbstractSMSTemplate',
    'SMSTemplate',
    'SMSTemplateDisallowedObject',
)


class OutputSMSMessage(BaseMessage):

    State = OutputSMSMessageState

    content = models.TextField(verbose_name=_('content'), null=False, blank=False, max_length=700)
    template = models.ForeignKey(settings.SMS_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='output_sms_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False,
                                choices=OutputSMSMessageState.choices, editable=False,
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
        return self.state in {OutputSMSMessageState.ERROR, OutputSMSMessageState.ERROR_RETRY}


class OutputSMSRelatedObject(BaseRelatedObject):

    output_sms_message = models.ForeignKey(OutputSMSMessage, verbose_name=_('output SMS message'), null=False,
                                           blank=False, on_delete=models.CASCADE, related_name='related_objects')

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('related object of a SMS message')
        verbose_name_plural = _('related objects of SMS messages')


class AbstractSMSTemplate(BaseAbstractTemplate):

    def get_controller(self):
        from pymess.backend.sms import SMSController
        return SMSController()

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
