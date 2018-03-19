from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist

from jsonfield.fields import JSONField

from chamber.models import SmartModel
from chamber.utils.datastructures import ChoicesNumEnum

from pymess.config import settings, get_email_sender

from .common import RelatedObjectManager


__ALL__ = (
    'EmailMessage',
    'EmailRelatedObject',
    'Attachment',
    'AbstractEmailTemplate',
    'EmailTemplate',
)


class EmailMessage(SmartModel):

    STATE = ChoicesNumEnum(
        ('WAITING', _('waiting'), 1),
        ('SENDING', _('sending'), 2),
        ('SENT', _('sent'), 3),
        ('ERROR', _('error'), 4),
        ('DEBUG', _('debug'), 5),
    )

    sent_at = models.DateTimeField(verbose_name=_('sent at'), null=True, blank=True, editable=False)
    recipient = models.EmailField(verbose_name=_('recipient'), blank=False, null=False)
    sender = models.EmailField(verbose_name=_('sender'), blank=False, null=False)
    sender_name = models.CharField(verbose_name=_('sender name'), blank=True, null=True, max_length=250)
    subject = models.TextField(verbose_name=_('subject'), blank=False, null=False)
    content = models.TextField(verbose_name=_('content'), null=False, blank=False)
    template_slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=True, blank=True, editable=False)
    template = models.ForeignKey(settings.EMAIL_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='email_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False, choices=STATE.choices, editable=False)
    backend = models.CharField(verbose_name=_('backend'), null=True, blank=True, editable=False, max_length=250)
    error = models.TextField(verbose_name=_('error'), null=True, blank=True, editable=False)
    extra_data = JSONField(verbose_name=_('extra data'), null=True, blank=True, editable=False)
    extra_sender_data = JSONField(verbose_name=_('extra sender data'), null=True, blank=True, editable=False)
    tag = models.SlugField(verbose_name=_('tag'), null=True, blank=True, editable=False)

    @property
    def friendly_sender(self):
        """
        returns sender with sender name in standard address format if sender name was defined
        """
        return '{} <{}>'.format(self.sender_name, self.sender) if self.sender_name else self.sender

    @property
    def failed(self):
        return self.state == self.STATE.ERROR

    class Meta:
        verbose_name = _('e-mail message')
        verbose_name_plural = _('e-mail messages')
        ordering = ('-created_at',)


class EmailRelatedObject(SmartModel):

    email_message = models.ForeignKey(EmailMessage, verbose_name=_('e-mail message'), null=False,
                                      blank=False, related_name='related_objects')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type of the related object'),
                                     null=False, blank=False)
    object_id = models.TextField(verbose_name=_('ID of the related object'), null=False, blank=False)
    object_id_int = models.PositiveIntegerField(verbose_name=_('ID of the related object in int format'), null=True,
                                                blank=True, db_index=True)

    objects = RelatedObjectManager()

    class Meta:
        verbose_name = _('related object of a e-mail message')
        verbose_name_plural = _('related objects of e-mail messages')
        ordering = ('-created_at',)


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

    email_message = models.ForeignKey(EmailMessage, verbose_name=_('e-mail message'), related_name='attachments')
    content_type = models.CharField(verbose_name=_('content type'), blank=False, null=False, max_length=100)
    file = models.FileField(verbose_name=_('file'), null=False, blank=False, upload_to='pymess/emails')

    objects = AttachmentManager()

    def __str__(self):
        return '#{}'.format(self.pk)

    class Meta:
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')


class AbstractEmailTemplate(SmartModel):

    slug = models.SlugField(verbose_name=_('slug'), max_length=100, null=False, blank=False, editable=False,
                            db_index=True)
    subject = models.TextField(verbose_name=_('subject'), blank=False, null=False)
    body = models.TextField(verbose_name=_('message body'), null=True, blank=False)
    sender = models.EmailField(verbose_name=_('sender'), null=True, blank=True, max_length=200)
    sender_name = models.CharField(verbose_name=_('sender name'), blank=True, null=True, max_length=250)

    def clean_body(self, context_data=None):
        try:
            self.render_body(context_data or {})
        except TemplateSyntaxError as ex:
            raise ValidationError(ugettext('Error during template body rendering: "{}"').format(ex))

    def clean_subject(self, context_data=None):
        try:
            self.render_subject(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(ugettext('Error during template subject rendering: "{}"').format(ex))

    def get_body(self):
        return self.body

    def get_subject(self):
        return self.subject

    def render_body(self, context_data):
        context_data = self._update_context_data(context_data)
        return Template(self.get_body()).render(Context(context_data))

    def render_subject(self, context_data):
        context_data = self._update_context_data(context_data)
        return Template(self.get_subject()).render(Context(context_data))

    def can_send(self, recipient, context_data):
        return True

    def _update_context_data(self, context_data):
        return context_data

    def send(self, recipient, context_data, related_objects=None, tag=None, attachments=None):
        if self.can_send(recipient, context_data):
            return get_email_sender().send(
                self.sender,
                recipient,
                self.render_subject(context_data),
                self.render_body(context_data),
                sender_name=self.sender_name,
                related_objects=related_objects,
                tag=tag,
                template=self,
                attachments=attachments
            )
        else:
            return None

    def __str__(self):
        return self.slug

    class Meta:
        abstract = True
        verbose_name = _('e-mail template')
        verbose_name_plural = _('e-mail templates')
        ordering = ('-created_at',)


class EmailTemplate(AbstractEmailTemplate):
    pass
