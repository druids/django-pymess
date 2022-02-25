from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from pymess.config import settings
from pymess.enums import DialerMessageState
from pymess.utils import normalize_phone_number

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject


__all__ = (
    'AbstractDialerMessage',
    'AbstractDialerTemplate',
    'DialerMessage',
    'DialerMessageRelatedObject',
    'DialerTemplate',
    'DialerTemplateDisallowedObject',
)


class AbstractDialerMessage(BaseMessage):

    State = DialerMessageState

    template = models.ForeignKey(settings.DIALER_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='dialer_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False,
                                choices=DialerMessageState.choices, editable=False,
                                db_index=True)
    is_autodialer = models.BooleanField(verbose_name=_('is autodialer'), null=False, default=True)
    number_of_status_check_attempts = models.PositiveIntegerField(verbose_name=_('number of status check attempts'),
                                                                  null=False, blank=False, default=0)
    content = models.TextField(verbose_name=_('content'), null=True, blank=True)

    class Meta(BaseMessage.Meta):
        abstract = True
        verbose_name = _('dialer message')
        verbose_name_plural = _('dialer messages')

    def clean(self):
        if self.is_autodialer and not self.content:
            raise ValidationError(_('Autodialer message must contain content.'))
        super().clean()

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    @property
    def failed(self):
        return self.state in {DialerMessageState.ERROR, DialerMessageState.ERROR_RETRY}


class DialerMessage(AbstractDialerMessage):

    is_final_state = models.BooleanField(verbose_name=_('is final state'), null=False, default=False)

    def __str__(self):
        return '{recipient}, {template_slug}, {state}'.format(
            recipient=self.recipient, template_slug=self.template_slug, state=self.get_state_display(),
        )


class DialerMessageRelatedObject(BaseRelatedObject):
    dialer_message = models.ForeignKey(DialerMessage, verbose_name=_('dialer message'), null=False,
                                       blank=False, on_delete=models.CASCADE, related_name='related_objects')

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('related object of a dialer message')
        verbose_name_plural = _('related objects of dialer messages')


class AbstractDialerTemplate(BaseAbstractTemplate):

    def get_controller(self):
        from pymess.backend.dialer import DialerController
        return DialerController()

    def send(self, recipient, context_data, related_objects=None, tag=None, **kwargs):
        return super().send(recipient, context_data, related_objects, tag, **kwargs)

    class Meta(BaseAbstractTemplate.Meta):
        abstract = True
        verbose_name = _('dialer template')
        verbose_name_plural = _('dialer templates')


class DialerTemplate(AbstractDialerTemplate):
    pass


class DialerTemplateDisallowedObject(BaseRelatedObject):

    template = models.ForeignKey(
        verbose_name=_('template'),
        to=DialerTemplate,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='disallowed_objects',
        db_index=True
    )

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('disallowed object of a dialer template')
        verbose_name_plural = _('disallowed objects of dialer templates')
