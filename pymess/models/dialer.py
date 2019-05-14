from chamber.utils.datastructures import ChoicesNumEnum
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from pymess.config import settings, get_dialer_sender
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

    STATE = ChoicesNumEnum(
        ('NOT_ASSIGNED', _('not assigned'), 0),
        ('READY', _('ready'), 1),
        ('RESCHEDULED_BY_DIALER', _('rescheduled by dialer'), 2),
        ('CALL_IN_PROGRESS', _('call in progress'), 3),
        ('HANGUP', _('hangup'), 4),
        ('DONE', _('done'), 5),
        ('RESCHEDULED', _('rescheduled'), 6),
        ('ANSWERED_COMPLETE', _('listened up complete message'), 7),
        ('ANSWERED_PARTIAL', _('listened up partial message'), 8),
        ('UNREACHABLE', _('unreachable'), 9),
        ('DECLINED', _('declined'), 10),
        ('UNANSWERED', _('unanswered'), 11),
        ('ERROR', _('error'), 66),
        ('DEBUG', _('debug'), 77),
    )

    template = models.ForeignKey(settings.DIALER_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='dialer_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    class Meta(BaseMessage.Meta):
        abstract = True
        verbose_name = _('dialer message')
        verbose_name_plural = _('dialer messages')


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

    def get_backend_sender(self):
        return get_dialer_sender()

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
