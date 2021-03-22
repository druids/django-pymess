from chamber.utils.datastructures import ChoicesNumEnum
from django.db import models
from django.utils.translation import ugettext_lazy as _

from pymess.config import settings

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject

__all__ = (
    'AbstractPushNotificationMessage',
    'AbstractPushNotificationTemplate',
    'PushNotificationMessage',
    'PushNotificationMessageRelatedObject',
    'PushNotificationTemplate',
)


class AbstractPushNotificationMessage(BaseMessage):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('SENT', _('sent'), 2),
        ('ERROR', _('error'), 3),
        ('DEBUG', _('debug'), 4),
        ('ERROR_RETRY', _('error retry'), 5),
    )

    template = models.ForeignKey(settings.PUSH_NOTIFICATION_TEMPLATE_MODEL, verbose_name=_('template'), blank=True,
                                 null=True, on_delete=models.SET_NULL, related_name='push_notifications')
    state = models.PositiveIntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices,
                                        editable=False, db_index=True)
    heading = models.TextField(verbose_name=_('heading'))
    url = models.URLField(verbose_name=_('URL'), null=True, blank=True)

    class Meta(BaseMessage.Meta):
        abstract = True
        verbose_name = _('push notification')
        verbose_name_plural = _('push notifications')

    @property
    def failed(self):
        return self.state in {self.STATE.ERROR, self.STATE.ERROR_RETRY}


class PushNotificationMessage(AbstractPushNotificationMessage):

    def __str__(self):
        return '{recipient}, {template_slug}, {state}'.format(recipient=self.recipient,
                                                              template_slug=self.template_slug, state=self.state)


class PushNotificationMessageRelatedObject(BaseRelatedObject):

    push_notification_message = models.ForeignKey(PushNotificationMessage, verbose_name=_('push notification message'),
                                                  null=False, blank=False, on_delete=models.CASCADE,
                                                  related_name='related_objects')

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('related object of a push notification message')
        verbose_name_plural = _('related objects of a push notification message')


class AbstractPushNotificationTemplate(BaseAbstractTemplate):

    heading = models.TextField(verbose_name=_('heading'))

    def get_controller(self):
        from pymess.backend.push import PushNotificationController
        return PushNotificationController()

    def send(self, recipient, context_data, related_objects=None, tag=None, **kwargs):
        return super().send(recipient, context_data, related_objects, tag,
                            state=AbstractPushNotificationMessage.STATE.WAITING,
                            heading=self.render_text_template(self.heading, context_data, recipient), **kwargs)

    class Meta(BaseAbstractTemplate.Meta):
        abstract = True
        verbose_name = _('push notification template')
        verbose_name_plural = _('push notification templates')


class PushNotificationTemplate(AbstractPushNotificationTemplate):
    pass
