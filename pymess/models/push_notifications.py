from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.template import Template, Context

from chamber.models import SmartModel
from chamber.shortcuts import get_object_or_none
from chamber.utils.datastructures import ChoicesNumEnum

from pymess.config import get_push_sender, get_push_template_model


class UserDevice(SmartModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), null=False, blank=False,
                             related_name='user_devices')
    registration_id = models.CharField(verbose_name=_('registration ID'), null=False, blank=False, max_length=256,
                                       db_index=True)
    is_active = models.BooleanField(verbose_name=_('is active'), default=True)
    device_id = models.CharField(verbose_name=_('device ID'), null=False, blank=False, max_length=255)

    def get_sns_arn(self):
        return (
            settings.AWS_ANDROID_SNS_APPLICATION_ARN if self.device_os == self.DEVICE_OS.ANDROID
            else settings.AWS_IOS_SNS_APPLICATION_ARN
        )

    def _post_save(self, change, *args, **kwargs):
        super()._post_save(change, *args, **kwargs)
        if self.is_active:
            UserDevice.objects.filter(
                device_id=self.device_id
            ).exclude(pk=self.pk).update(is_active=False)

    class Meta:
        app_label = 'pymess'
        verbose_name = _('user device')
        verbose_name_plural = _('user devices')
        ordering = ('-created_at',)

    class RESTMeta:
        fields = ('registration_id', 'is_active', 'device_id')


class AbstractPushNotification(SmartModel):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('SENT', _('sent'), 2),
        ('ERROR', _('error'), 3),
        ('DEBUG', _('debug'), 4),
    )

    user_device = models.ForeignKey('pymess.UserDevice', verbose_name=_('user device ID'), null=False, blank=False)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False)
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True)
    backend = models.SlugField(verbose_name=_('backend'), null=False, blank=False)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True)

    def template(self):
        return get_object_or_none(get_push_template_model(), slug=self.template_slug) or self.template_slug
    template.short_description = _('template')

    class Meta:
        abstract = True
        verbose_name = _('push notification')
        verbose_name_plural = _('push notifications')
        ordering = ('-created_at',)


class AbstractPushNotificationTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, primary_key=True,
                            editable=False)
    body = models.TextField(null=True, blank=False, verbose_name=_('notification body'), max_length=250)

    def render(self, user, context):
        return Template(self.body).render(Context(context))

    def send(self, user, context):
        get_push_sender().send(user, self.render(user, context))

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        verbose_name = _('push notification template')
        verbose_name_plural = _('push notification templates')
