from chamber.models import SmartModel
from chamber.utils.datastructures import ChoicesNumEnum
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist

from pymess.config import settings, get_email_sender

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject


__all__ = (
    'EmailMessage',
    'EmailRelatedObject',
    'Attachment',
    'AbstractEmailTemplate',
    'EmailTemplate',
)


class EmailMessage(BaseMessage):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('SENDING', _('sending'), 2),
        ('SENT', _('sent'), 3),
        ('ERROR', _('error'), 4),
        ('DEBUG', _('debug'), 5),
    )

    recipient = models.EmailField(verbose_name=_('recipient'), blank=False, null=False)
    template = models.ForeignKey(settings.EMAIL_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='email_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    sender = models.EmailField(verbose_name=_('sender'), blank=False, null=False)
    sender_name = models.CharField(verbose_name=_('sender name'), blank=True, null=True, max_length=250)
    subject = models.TextField(verbose_name=_('subject'), blank=False, null=False)
    number_of_send_attempts = models.PositiveIntegerField(verbose_name=_('number of send attempts'), null=False,
                                                          blank=False, default=0)

    @property
    def friendly_sender(self):
        """
        returns sender with sender name in standard address format if sender name was defined
        """
        return '{} <{}>'.format(self.sender_name, self.sender) if self.sender_name else self.sender

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    def __str__(self):
        return '{}: {}'.format(self.recipient, self.subject)

    class Meta(BaseMessage.Meta):
        verbose_name = _('e-mail message')
        verbose_name_plural = _('e-mail messages')


class EmailRelatedObject(BaseRelatedObject):

    email_message = models.ForeignKey(EmailMessage, verbose_name=_('e-mail message'), null=False, blank=False,
                                      on_delete=models.CASCADE, related_name='related_objects')

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('related object of a e-mail message')
        verbose_name_plural = _('related objects of e-mail messages')


class AttachmentManager(models.Manager):

    def create_from_tripple(self, tripple):
        filename, file, content_type = tripple
        attachment = self.model(
            email_message=self.instance,
            content_type=content_type
        )
        attachment.file.save(filename, file, save=True)
        return attachment

    def create_from_tripples(self, *tripples):
        return [
            self.create_from_tripple(tripple) for tripple in tripples
        ]


class Attachment(SmartModel):

    email_message = models.ForeignKey(EmailMessage, verbose_name=_('e-mail message'), on_delete=models.CASCADE,
                                      related_name='attachments')
    content_type = models.CharField(verbose_name=_('content type'), blank=False, null=False, max_length=100)
    file = models.FileField(verbose_name=_('file'), null=False, blank=False, upload_to='pymess/emails')

    objects = AttachmentManager()

    def __str__(self):
        return '#{}'.format(self.pk)

    class Meta:
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')


class AbstractEmailTemplate(BaseAbstractTemplate):

    subject = models.TextField(verbose_name=_('subject'), blank=False, null=False)
    sender = models.EmailField(verbose_name=_('sender'), null=True, blank=True, max_length=200)
    sender_name = models.CharField(verbose_name=_('sender name'), blank=True, null=True, max_length=250)

    def clean_subject(self, context_data=None):
        try:
            self.render_subject(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(ugettext('Error during template subject rendering: "{}"').format(ex))

    def get_subject(self):
        return self.subject

    def render_subject(self, context_data):
        context_data = self._update_context_data(context_data)
        return Template(self.get_subject()).render(Context(context_data))

    def get_backend_sender(self):
        return get_email_sender()

    def send(self, recipient, context_data, related_objects=None, tag=None, attachments=None, **kwargs):
        return super().send(
            recipient=recipient,
            context_data=context_data,
            related_objects=related_objects,
            tag=tag,
            sender=self.sender,
            subject=self.render_subject(context_data),
            sender_name=self.sender_name,
            attachments=attachments
        )

    class Meta(BaseAbstractTemplate.Meta):
        abstract = True
        verbose_name = _('e-mail template')
        verbose_name_plural = _('e-mail templates')


class EmailTemplate(AbstractEmailTemplate):
    pass
