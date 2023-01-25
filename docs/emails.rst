.. _emails:

E-mails
=======

Like SMS E-mail messages are stored inside Django model class and sent via backend. Again we provide more e-mail backends, every backend uses different e-mail service like Mandrill, AWS SNS or standard SMTP. For sending e-mail message you can use function ``pymess.backend.email.send`` or ``pymwess.backend.email.send_template``.

.. function:: pymess.backend.emails.send(sender, recipient, subject, content, sender_name=None, related_objects=None, attachments=None, tag=None, send_immediately=False, **kwargs)

  Parameter ``sender`` define source e-mail address of the message, you can specify the name of the sender with optional parameter ``sender_name``.  ``recipient`` is destination e-mail address. Subject and HTML content of the e-mail message is defined with  ``subject`` and ``content`` parameters. Attribute ``related_objects`` should contain a list of objects that you want to connect with the send message (with generic relation). Optional parameter ``attachments`` should contains list of files that will be sent with the e-mail in format ``({file name}, {output stream with file content}, {content type})``.  ``tag`` is string mark which is stored with the sent SMS message . The last non required parameter ``**email_kwargs`` is extra data that will be stored inside e-mail message model in field ``extra_data``.

.. function:: pymess.backend.emails.send_template(recipient, slug, context_data, related_objects=None, attachments=None, tag=None, send_immediately=False)

  The second function is used for sending prepared templates that are stored inside template model (class that extends ``pymess.models.sms.AbstractEmailTemplate``). The first parameter ``recipient`` is e-mail address of the receiver, ``slug`` is key of the template, ``context_data`` is a dictionary that contains context data for rendering e-mail content from the template, ``related_objects`` should contains list of objects that you want to connect with the send message, ``attachments`` should contains list of files that will be send with the e-mail and ``tag`` is string mark which is stored with the sent SMS message.

Models
------

.. class:: pymess.models.emails.EmailMessage

  The model contains data of already sent e-mail messages.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: sent_at

    Django ``DateTimeField``, contains date and time of sending the e-mail message.

  .. attribute:: recipient

    ``EmailField`` that contains e-mail address of the receiver.

  .. attribute:: sender

    ``EmailField`` that contains e-mail address of th sender.

  .. attribute:: sender_name

    ``CharField`` that contains readable/friendly sender name.

  .. attribute:: subject

    ``TextField``, contains subject of the e-mail message.

  .. attribute:: content

    ``cached_property``, returns content of the e-mail message, which is saved in a file.

  .. attribute:: template_slug

    If e-mail was sent from the template, this attribute contains key of the template.

  .. attribute:: template

    If e-mail was sent from the template, this attribute contains foreign key of the template. The reason why there is ``template_slug`` and ``template`` fields is that a template instance can be removed and it is good to keep at least the key of the template.

  .. attribute:: state

    Contains the current state of the message. Allowed states are:

      * DEBUG - e-mail was not sent because system is in debug mode
      * ERROR - error was raised during sending of the e-mail message
      * ERROR_RETRY - error was raised during sending of the e-mail message, message will be retried
      * SENDING - e-mail was sent to the external service
      * SENT - e-mail was sent to the receiver
      * WAITING - e-mail was not sent to the external service

  .. attribute:: backend

    Field contains path to the e-mail backend that was used for sending of the SMS message.

  .. attribute:: error

    If error was raised during sending of the SMS message this field contains text description of the error.

  .. attribute:: extra_data

    Extra data stored with ``JSONField``.

  .. attribute:: extra_sender_data

    Extra data related to the e-mail backend stored with ``JSONField``. Every SMS backend can have different extra data.

  .. attribute:: tag

    String tag that you can define during sending SMS message.

  .. attribute:: number_of_send_attempts

    Number of sending attempts. Value is set only when batch sending is used.

  .. attribute:: retry_sending

    Defines if message should be resent if sending failed.

  .. attribute:: external_id

    Message identifier on the provider side, can be ``None`` if backend doesn't support it.

  .. attribute:: info_changed_at

    Date and time of last message status update.

  .. attribute:: last_webhook_received_at

    Date and time of last status change received from provider via webhook.

  .. attribute:: related_objects

    Returns DB manager of ``pymess.models.emails.EmailRelatedObject`` model that are related to the concrete e-mail message.


.. class:: pymess.models.emails.EmailRelatedObject

  Model for storing related objects that you can connect with the e-mail message.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: email_message

    Foreign key to the e-mail message.

  .. attribute:: content_type

    Content type of the stored model (generic relation)

  .. attribute:: object_id

    Primary key of a related object stored in django ``TextField``.


.. class:: pymess.models.emails.Attachment

  Django model that contains e-mail attachments.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: email_message

    Foreign key to the e-mail message.

  .. attribute:: content_type

    Django ``CharField``, contains content type of the attachment.

  .. attribute:: file

    Django ``FileField``, contains file which was send to the recipient.


.. class:: pymess.models.emails.AbstractEmailTemplate

  Abstract class of e-mail template which you can use to define your own e-mail template model. Your model that extends this class is set inside setting ``PYMESS_EMAIL_TEMPLATE_MODEL``::

      PYMESS_EMAIL_TEMPLATE_MODEL = 'your_application.YourEmailTemplateModel'

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: slug

    Key of the e-mail template in the string format (Django slug).

  .. attribute:: sender

    ``EmailField`` that contains e-mail address of the sender.

  .. attribute:: sender_name

    ``CharField`` that contains readable/friendly sender name.

  .. attribute:: subject

    ``TextField``, contains subject of the e-mail message. Final e-mail subject is rendered with Django template system by default.

  .. attribute:: body

    Body of the e-mail message. Final e-mail content is rendered with Django template system by default.

  .. attribute:: is_active

    Sets whether the template is active and should be sent or not.

  .. method:: get_body()

    Returns body of the model message. You can use it to update e-mail body before rendering.

  .. method:: render_body(context_data)

    Renders template stored inside ``body`` field to the message content. Standard Django template system is used by default.

  .. method:: get_subject()

    Returns subject of the model message. You can use it to update e-mail subject before rendering.

  .. method:: render_subject(context_data)

    Renders template stored inside ``subject`` field to the message content. Standard Django template system is used by default.

  .. method:: can_send(recipient, context_data)

    Returns by default the value of ``is_active``. If you need to restrict sending e-mail template for some reasons, you can override this method.

  .. method:: send(recipient, context_data, related_objects=None, tag=None, attachments=None)

    Checks if message can be sent, renders message content and sends it via defined backend. Finally, the sent message is returned. If message cannot be sent, ``None`` is returned.

.. class:: pymess.models.emails.EmailTemplate

  Default template model class that only inherits from ``pymess.models.emails.AbstractEmailTemplate``


Backends
--------

Backend is a class that is used for sending messages. Every backend must provide API defined by ``pymess.backends.emails.EmailBackend`` class. E-mail backend is configured via ``PYMESS_EMAIL_SENDER_BACKEND`` (ex. ``PYMESS_EMAIL_SENDER_BACKEND = 'pymess.backend.emails.smtp.SMTPEmailBackend'``). There are currently implemented following e-mail backends:

.. class:: pymess.backend.emails.dummy.DummyEmailBackend

  Backend that can be used for testing. E-mail is not sent, but is automatically set to the ``DEBUG`` state.

.. class:: pymess.backend.emails.smtp.SMTPEmailBackend

  Backend that uses standard SMTP service for sending e-mails. Configuration of SMTP is same as Django configuration.

.. class:: pymess.backend.emails.mandrill.MandrillEmailBackend

  Backend that uses mandrill service for sending e-mail messages (https://mandrillapp.com/api/docs/index.python.html). For this purpose you must have installed ``mandrill`` library.

  Configuration of attributes according to Mandrill operator documentation (the names of the configuration are the same)::

    PYMESS_EMAIL_MANDRILL_CONFIG = {
        'KEY': '',  # Mandrill notification key
        'HEADERS': None,
        'TRACK_OPENS': False,
        'TRACK_CLICKS': False,
        'AUTO_TEXT': False,
        'INLINE_CSS': False,
        'URL_STRIP_QS': False,
        'PRESERVE_RECIPIENTS': False,
        'VIEW_CONTENT_LINK': True,
        'ASYNC': False,
    }


Custom backend
^^^^^^^^^^^^^^

If you want to write your own Pymess e-mail backend, you must create class that inherits from ``pymess.backends.emails.EmailBackend``::

.. class pymess.backends.sms.EmailBackend

  .. method:: publish_message(message)

    This method should send e-mail message (obtained from the input argument) and update its state. This method must be overridden in the custom backend.

Commands
--------

``send_messages_batch``
^^^^^^^^^^^^^^^^^^^^^^^

As mentioned e-mails can be sent in a batch with Django command ``send_messages_batch --type=email``.

``sync_emails``
^^^^^^^^^^^^^^^

Store e-mail body in a HTML file is better from code readability. Therefore this command updates e-mails body from HTML files store in directory. You can select the directory with command property ``directory`` or you can set directory with setting ``PYMESS_EMAIL_HTML_DATA_DIRECTORY``. E-mails body in the directory is stored like HTML file named with e-mail slug and html as a suffix.

``dump_emails``
^^^^^^^^^^^^^^^

E-mail body can be changed in the database therefore reverse operation to ``sync_emails`` can be done with this command. You must select directory where e-mails body in HTML format will be stored.


``pull_emails_info``
^^^^^^^^^^^^^^^^^^^^

Synchronize e-mail message status from the provider.

Webhooks
--------

Mandrill provides notification system which notifies your URL endpoint that some message status was changed. For this purpose pymess provides view ``pymess.webhooks.mandrill.MandrillWebhookView`` which you simply add to your ``django urls``. Every notification will mark message to be updated with the ``pull_emails_info`` command.


Migrations
----------

The library provides utilities to migrate e-mail templates into database. The e-mail bodies can be stored in the files with path defined in the setting ``EMAIL_HTML_DATA_DIRECTORY``. Every file should be named its the template slug. You can use the ``pymess.utils.migrations.SyncEmailTemplates`` migration helper to sync e-mail body as in the example::

    # Django settings
    EMAIL_HTML_DATA_DIRECTORY = '/data/emails

    # data/emails directory
    data/emails
        - set-pasword.html
        - welcome.html

    # Migration
    from django.db import migrations
    from pymess.utils.migrations import SyncEmailTemplates


    class Migration(migrations.Migration):

        dependencies = [
            ('communication', '0001_migration'),
        ]

        operations = [
            migrations.RunPython(SyncEmailTemplates(('set-password', 'welcome))),  # Body of the e-mails will be updated (e-mail templates must exist in the database)
        ]
