import import_string
from pathlib import Path
from uuid import uuid4

from chamber.models import SmartModel

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.functional import cached_property
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist

from pymess.config import settings
from pymess.enums import EmailMessageState
from pymess.utils.html import raise_error_if_contains_banned_tags

from .common import BaseAbstractTemplate, BaseMessage, BaseRelatedObject, MessageQueryset


__all__ = (
    'EmailMessage',
    'EmailRelatedObject',
    'EmailTemplate',
    'Attachment',
    'AbstractEmailTemplate',
    'EmailTemplateDisallowedObject',
    'EmailTemplateAttachment',
)


def generate_content_filename(instance, filename):
    return Path(settings.EMAIL_STORAGE_PATH) / 'contents' / 'content_{}.txt'.format(uuid4())


def generate_attachment_filename(instance, filename):
    return Path(settings.EMAIL_STORAGE_PATH) / 'attachments' / filename


def generate_template_attachment_filename(instance, filename):
    return Path(settings.EMAIL_STORAGE_PATH) / 'template_attachments' / filename


class EmailMessageQuerySet(MessageQueryset):

    def create(self, content, **kwargs):
        message = self.model(**kwargs)
        message.content_file.save(None, ContentFile(content.encode()))
        return message


class EmailMessage(BaseMessage):

    State = EmailMessageState

    recipient = models.EmailField(verbose_name=_('recipient'), blank=False, null=False, db_index=True)
    template = models.ForeignKey(settings.EMAIL_TEMPLATE_MODEL, verbose_name=_('template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='email_messages')
    state = models.IntegerField(verbose_name=_('state'), null=False, blank=False,
                                choices=EmailMessageState.choices, editable=False,
                                db_index=True)
    sender = models.EmailField(verbose_name=_('sender'), blank=False, null=False)
    sender_name = models.CharField(verbose_name=_('sender name'), blank=True, null=True, max_length=250)
    subject = models.TextField(verbose_name=_('subject'), blank=False, null=False)
    external_id = models.CharField(verbose_name=_('external ID'), blank=True, null=True, db_index=True, max_length=250)
    last_webhook_received_at = models.DateTimeField(
        verbose_name=_('last webhook received at'),
        null=True,
        blank=True,
        editable=False,
    )
    info_changed_at = models.DateTimeField(
        verbose_name=_('info changed at'),
        null=True,
        blank=True,
        editable=False,
    )
    content_file = models.FileField(
        verbose_name=_('content file'),
        null=False,
        blank=False,
        upload_to=generate_content_filename,
    )

    objects = EmailMessageQuerySet.as_manager()

    class Meta(BaseMessage.Meta):
        verbose_name = _('e-mail message')
        verbose_name_plural = _('e-mail messages')

    def __str__(self):
        return '{}: {}'.format(self.recipient, self.subject)

    @property
    def friendly_sender(self):
        """
        returns sender with sender name in standard address format if sender name was defined
        """
        return '{} <{}>'.format(self.sender_name, self.sender) if self.sender_name else self.sender

    @property
    def failed(self):
        return self.state in {EmailMessageState.ERROR, EmailMessageState.ERROR_RETRY}

    @cached_property
    def content(self):
        return self.content_file.read().decode()


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
            content_type=content_type,
            filename=filename
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
    file = models.FileField(verbose_name=_('file'), null=False, blank=False,
                            upload_to=generate_attachment_filename)
    filename = models.CharField(verbose_name=_('filename'), blank=True, null=True, max_length=100)

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

    def get_controller(self):
        from pymess.backend.emails import EmailController
        return EmailController()

    def _update_context_data(self, context_data, recipient):
        for context_processor_fun_name in settings.EMAIL_TEMPLATE_CONTEXT_PROCESSORS:
            context_data.update(import_string(context_processor_fun_name)(context_data, self, recipient))
        return context_data

    def clean_subject(self, context_data=None):
        try:
            self.render_subject(context_data or {})
        except (TemplateSyntaxError, TemplateDoesNotExist) as ex:
            raise ValidationError(ugettext('Error during template subject rendering: "{}"').format(ex))

    def get_subject(self):
        return self.subject

    def render_subject(self, context_data, recipient=None):
        context_data = self._update_context_data(context_data, recipient)
        return Template(self.get_subject()).render(Context(context_data))

    def send(self, recipient, context_data, related_objects=None, tag=None, attachments=None,
             priority=settings.DEFAULT_MESSAGE_PRIORITY, **kwargs):
        return super().send(
            recipient=recipient,
            context_data=context_data,
            related_objects=related_objects,
            tag=tag,
            sender=self.sender,
            subject=self.render_subject(context_data),
            sender_name=self.sender_name,
            priority=priority,
            attachments=attachments,
            **kwargs,
        )

    class Meta(BaseAbstractTemplate.Meta):
        abstract = True
        verbose_name = _('e-mail template')
        verbose_name_plural = _('e-mail templates')


class EmailTemplate(AbstractEmailTemplate):

    def clean_body(self, context_data=None):
        super().clean_body(context_data={'EMAIL_DISABLE_VARIABLE_VALIDATOR': True})
        raise_error_if_contains_banned_tags(self.body)

    def clean_subject(self, context_data=None):
        super().clean_subject(context_data={'EMAIL_DISABLE_VARIABLE_VALIDATOR': True})
        raise_error_if_contains_banned_tags(self.subject)

    def _extend_body(self, template_body):
        base_template = settings.EMAIL_TEMPLATE_BASE_TEMPLATE
        templatetags = settings.EMAIL_TEMPLATE_TEMPLATETAGS

        template_content = '{{% block {} %}}{}{{% endblock %}}'.format(
            settings.EMAIL_TEMPLATE_CONTENT_BLOCK,
            template_body
        )

        out = []
        if base_template is not None:
            out.append('{{% extends \'{}\' %}}'.format(base_template))
        if templatetags:
            out.append('{{% load {} %}}'.format(' '.join(templatetags)))
        out.append(template_content)

        return ''.join(out)

    def get_body(self):
        return self._extend_body(self.body) if settings.EMAIL_TEMPLATE_EXTEND_BODY else self.body

    def send(self, recipient, context_data, related_objects=None, tag=None, attachments=None, **kwargs):
        attachments = [] if attachments is None else attachments
        attachments += [
            (
                template_attachment.filename or os.path.basename(template_attachment.file.name),
                ContentFile(template_attachment.file.read()),
                template_attachment.content_type,
            ) for template_attachment in self.template_attachments.all()
        ]

        return super().send(
            recipient=recipient,
            context_data=context_data,
            related_objects=related_objects,
            tag=tag,
            attachments=attachments,
            **kwargs,
        )


class EmailTemplateDisallowedObject(BaseRelatedObject):

    template = models.ForeignKey(
        verbose_name=_('template'),
        to=EmailTemplate,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='disallowed_objects',
        db_index=True
    )

    class Meta(BaseRelatedObject.Meta):
        verbose_name = _('disallowed object of an e-mail template')
        verbose_name_plural = _('disallowed objects of e-mail templates')


class EmailTemplateAttachment(SmartModel):

    template = models.ForeignKey(to=settings.EMAIL_TEMPLATE_MODEL, verbose_name=_('template'),
                                 on_delete=models.CASCADE, related_name='template_attachments')
    content_type = models.CharField(verbose_name=_('content type'), blank=False, null=False, max_length=100)
    file = models.FileField(verbose_name=_('file'), null=False, blank=False,
                            upload_to=generate_template_attachment_filename)
    filename = models.CharField(verbose_name=_('filename'), blank=True, null=True, max_length=100)

    class Meta:
        verbose_name = _('e-mail template attachment')
        verbose_name_plural = _('e-mail template attachments')
