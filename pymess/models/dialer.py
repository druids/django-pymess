from chamber.models import SmartModel
from chamber.utils.datastructures import ChoicesNumEnum
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.encoding import force_text
from jsonfield.fields import JSONField

from pymess.config import settings, get_dialer_sender
from pymess.utils import normalize_phone_number

from .common import RelatedObjectManager

__ALL__ = (
    'AbstractDialerMessage',
    'AbstractDialerTemplate',
    'DialerMessage',
    'DialerMessageRelatedObject',
    'DialerTemplate',
)


class AbstractDialerMessage(SmartModel):

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

    sent_at = models.DateTimeField(verbose_name=_('sent at'), null=True, blank=True, editable=False)
    recipient = models.CharField(verbose_name=_('recipient'), null=False, blank=False, max_length=20)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    template = models.ForeignKey(settings.DIALER_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='dialer_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.CharField(verbose_name=_('backend'), null=True, blank=True, editable=False, max_length=250)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)
    extra_data = JSONField(verbose_name=_('extra data'), null=True, blank=True, editable=False)
    extra_sender_data = JSONField(verbose_name=_('extra sender data'), null=True, blank=True, editable=False)
    tag = models.SlugField(verbose_name=_('tag'), null=True, blank=True, editable=False)

    def clean_recipient(self):
        self.recipient = normalize_phone_number(force_text(self.recipient))

    def clean_content(self):
        pass

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    def __str__(self):
        return self.recipient

    class Meta:
        abstract = True
        verbose_name = _('dialer message')
        verbose_name_plural = _('dialer messages')
        ordering = ('-created_at',)


class DialerMessage(AbstractDialerMessage):

    is_final_state = models.BooleanField(verbose_name=_('is final state'), null=False, default=False)

    def __str__(self):
        return '{recipient}, {template_slug}, {state}'.format(
            recipient=self.recipient, template_slug=self.template_slug, state=self.get_state_display(),
        )


class DialerMessageRelatedObject(SmartModel):

    dialer_message = models.ForeignKey(DialerMessage, verbose_name=_('dialer message'), null=False,
                                       blank=False, on_delete=models.CASCADE, related_name='related_objects')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type of the related object'),
                                     null=False, blank=False, on_delete=models.CASCADE)
    object_id = models.TextField(verbose_name=_('ID of the related object'), null=False, blank=False)
    object_id_int = models.PositiveIntegerField(verbose_name=_('ID of the related object in int format'), null=True,
                                                blank=True, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = RelatedObjectManager()

    class Meta:
        verbose_name = _('related object of a dialer message')
        verbose_name_plural = _('related objects of dialer messages')
        ordering = ('-created_at',)


class AbstractDialerTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, editable=False,
                            primary_key=True)
    body = models.TextField(verbose_name=_('message body'), null=True, blank=False)

    def _update_context_data(self, context_data):
        return context_data

    def clean_body(self, context_data=None):
        try:
            self.render_body(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(ugettext('Error during template body rendering: "{}"').format(ex))

    def get_body(self):
        return self.body

    def render_body(self, context_data):
        context_data = self._update_context_data(context_data)
        return Template(self.get_body()).render(Context(context_data))

    def can_send(self, recipient, context_data):
        return True

    def send(self, recipient, context_data, related_objects=None, tag=None, **kwargs):
        if self.can_send(recipient, context_data):
            return get_dialer_sender().send(
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
        verbose_name = _('dialer template')
        verbose_name_plural = _('dialer templates')
        ordering = ('-created_at',)


class DialerTemplate(AbstractDialerTemplate):
    pass
