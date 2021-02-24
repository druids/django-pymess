.. _installation:

Installation
============

Using PIP
---------

Django can use pip for installation:

.. code-block:: console

    $ pip install django-pymess


Configuration
=============

After installation you must go through these steps:

Required Settings
-----------------

The following variables have to be added to or edited in the project's ``settings.py``:

For using pymess you just add ``pymess`` to ``INSTALLED_APPS`` variable::

    INSTALLED_APPS = (
        ...
        'pymess',
        ...
    )

Setup
-----

SMS
^^^

.. attribute:: PYMESS_SMS_TEMPLATE_MODEL

  If you want to use your own SMS template model you must set this setting with your custom SMS template model that extends ``pymess.models.sms.AbstractSMSTemplate`` otherwise ``pymess.models.sms.SMSTemplate`` is used.

.. attribute:: PYMESS_SMS_USE_ACCENT

  Setting that sets if SMS will be sent with accent or not. Default value is ``False``.

.. attribute:: PYMESS_SMS_LOG_IDLE_MESSAGES

  Setting that sets whether the delivery time is checked for messages. Default value is ``True``.

.. attribute:: SMS_SET_ERROR_TO_IDLE_MESSAGES

  Setting that sets if idle messages will be moved to the error state after defined time. Default value is ``True``.

.. attribute:: PYMESS_SMS_IDLE_MESSAGES_TIMEOUT_MINUTES

  If setting ``PYMESS_SMS_LOG_IDLE_MESSAGES`` is set to ``True``, ``PYMESS_SMS_IDLE_SENDING_MESSAGES_TIMEOUT_MINUTES`` defines the number of minutes to send a warning that sms has not been sent. Default value is ``10``.

.. attribute:: PYMESS_SMS_DEFAULT_PHONE_CODE

  Country code that is set to the recipient if phone number doesn't contain another one.

.. attribute:: PYMESS_SMS_SENDER_BACKEND

  Path to the SMS backend that will be used for sending SMS messages. Default value is ``'pymess.backend.sms.dummy.DummySMSBackend'``.

.. attribute:: PYMESS_SMS_BATCH_SENDING

  Because sending messages speed is dependent on the provider which can slow down your application speed, messages can be send in background with command ``send_messages_batch``. Default value is ``False``.

.. attribute:: PYMESS_SMS_BATCH_SIZE

  Defines maximum number of messages that are sent with command ``send_messages_batch``.

.. attribute:: PYMESS_SMS_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

  Defines maximum number of attempts for sending one message. Default value is ``3``.

.. attribute:: PYMESS_SMS_BATCH_MAX_SECONDS_TO_SEND

   Defines maximum number of seconds to try to send a SMS message that ended in an ``ERROR_RETRY`` state. Default value is ``60 * 60`` (1 hour).

E-MAIL
^^^^^^

.. attribute:: PYMESS_EMAIL_TEMPLATE_MODEL

  If you want to use your own e-mail template model you must set this setting with your custom e-mail template model that extends ``pymess.models.email.AbstractEmailTemplate`` otherwise is used ``pymess.models.email.EmailTemplate``.

.. attribute:: PYMESS_EMAIL_TEMPLATE_BASE_TEMPLATE

  Path to the file containing an e-mail content in the Django template system format.

.. attribute:: PYMESS_EMAIL_TEMPLATE_TEMPLATETAGS

  List of Django templatetags loaded in the template file.

.. attribute:: PYMESS_EMAIL_TEMPLATE_CONTENT_BLOCK

  Name of the template block which contains e-mail body.

.. attribute:: PYMESS_EMAIL_TEMPLATE_CONTEXT_PROCESSORS

  List of Django template context processors.

.. attribute:: PYMESS_EMAIL_TEMPLATE_EXTEND_BODY

  Setting defines if an e-mail message body will be extended with content block and templatetags.

.. attribute:: PYMESS_EMAIL_TEMPLATE_BANNED_TAGS

  List of HTML tags which cannot be used in the e-mail content.

.. attribute:: PYMESS_EMAIL_SENDER_BACKEND

  Path to the E-mail backend that will be used for sending e-mail messages. Default value is ``'pymess.backend.emails.dummy.DummyEmailBackend'``.

.. attribute:: PYMESS_EMAIL_BATCH_SENDING

  If you use standard SMTP service you should send e-mails in batches otherwise other SMTP providers could add your SMTP server to the black-list. With this setting you configure e-mail backend not to send e-mails directly but messages are only created in state "waiting". Finally e-mails should be sent with Django command ``send_messages_batch``. Default value is ``False``.

.. attribute:: PYMESS_EMAIL_BATCH_SIZE

  Defines maximum number of e-mails that are sent with command ``send_messages_batch``.

.. attribute:: PYMESS_EMAIL_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

  Defines maximum number of attempts for sending one e-mail message. Default value is ``3``.

.. attribute:: PYMESS EMAIL_BATCH_MAX_SECONDS_TO_SEND

   Defines maximum number of seconds to try to send an e-mail message that ended in an ``ERROR_RETRY`` state. Default value is ``60 * 60`` (1 hour).

.. attribute:: PYMESS_EMAIL_PULL_INFO_MAX_TIMEOUT_FROM_SENT_SECONDS

  Defines delay in seconds from the time the message was sent to message info can be pulled from the provider.

.. attribute:: PYMESS_EMAIL_PULL_INFO_DELAY_SECONDS

  Defines delay in seconds from the time the message change notification was received to message info will be pulled from the provider.

.. attribute:: PYMESS_EMAIL_STORAGE_PATH

  Path for storing e-mail attachments and contents (bodies).
  If changed after initial migration, existing files must be moved manually via data migration.


DIALER
^^^^^^

.. attribute:: PYMESS_DIALER_TEMPLATE_MODEL

  If you want to use your own dialer template model you must set this setting with your custom dialer template model that extends ``pymess.models.dialer.AbstractDialerMessage`` otherwise is used ``pymess.models.dialer.DialerMessage``.

.. attribute:: PYMESS_DIALER_SENDER_BACKEND

  Path to the dialer backend that will be used for sending dialer messages. Default value is ``'pymess.backend.dialer.dummy.DummyDialerBackend'``.

.. attribute:: PYMESS_DIALER_BATCH_SENDING

  Because sending messages speed is dependent on the provider which can slow down your application speed, messages can be send in background with command ``send_messages_batch``. Default value is ``False``.

.. attribute:: PYMESS_DIALER_BATCH_SIZE

  Defines maximum number of messages that are sent with command ``send_messages_batch``.

.. attribute:: PYMESS_DIALER_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

  Defines maximum number of attempts for sending one dialer message. Default value is ``3``.

.. attribute:: PYMESS_DIALER_BATCH_MAX_SECONDS_TO_SEND

  Defines maximum number of seconds to try to send a dialer message that ended in an ``ERROR_RETRY`` state. Default value is ``60 * 60`` (1 hour).

.. attribute:: PYMESS_DIALER_IDLE_MESSAGES_TIMEOUT_MINUTES

  Number of minutes which dialer backend will try to check message state. Default value is ``24h``

.. attribute:: PYMESS_DIALER_NUMBER_OF_STATUS_CHECK_ATTEMPTS

  Number of check attempts to get dialer message state. Default value is ``5``


Push notifications
^^^^^^^^^^^^^^^^^^

.. attribute:: PYMESS_PUSH_NOTIFICATION_TEMPLATE_MODEL

  If you want to use your own push notification template model you must set this setting with your custom push notification template model that extends ``pymess.models.push.AbstractPushNotificationMessage`` otherwise is used ``pymess.models.push.PushNotificationMessage``.

.. attribute:: PYMESS_PUSH_NOTIFICATION_SENDER_BACKEND

  Path to the push notification backend that will be used for sending push notifications. Default value is ``'pymess.backend.push.dummy.DummyPushNotificationBackend'``.

.. attribute:: PYMESS_PUSH_NOTIFICATION_BATCH_SENDING

  Because sending messages speed is dependent on the provider which can slow down your application speed, messages can be send in background with command ``send_messages_batch``. Default value is ``False``.

.. attribute:: PYMESS_PUSH_NOTIFICATION_BATCH_SIZE

  Defines maximum number of messages that are sent with command ``send_messages_batch``.

.. attribute:: PYMESS_PUSH_NOTIFICATION_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

  Defines maximum number of attempts for sending one push notification message. Default value is ``3``.

.. attribute:: PYMESS_PUSH_NOTIFICATION_BATCH_MAX_SECONDS_TO_SEND

  Defines maximum number of seconds to try to send an push notification message that ended in an ``ERROR_RETRY`` state. Default value is ``60 * 60`` (1 hour).
