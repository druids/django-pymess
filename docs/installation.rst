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

.. attribute:: PYMESS_SMS_ATS_CONFIG

  Configuration of ``pymess.backend.sms.ats_sms_operator.ATSSMSBackend``.

.. attribute:: PYMESS_SMS_OPERATOR_CONFIG

  Configuration of ``pymess.backend.sms.sms_operator.SMSOperatorBackend``.

.. attribute:: PYMESS_SMS_SNS_CONFIG

  Configuration of ``pymess.backend.sms.sns.SNSSMSBackend``.

E-MAIL
^^^^^^

.. attribute:: PYMESS_EMAIL_TEMPLATE_MODEL

  If you want to use your own E-MAIL template model you must set this setting with your custom e-mail template model that extends ``pymess.models.email.AbstractEmailTemplate`` otherwise is used ``pymess.models.email.EmailTemplate``.

.. attribute:: PYMESS_EMAIL_SENDER_BACKEND

  Path to the E-mail backend that will be used for sending e-mail messages. Default value is ``'pymess.backend.emails.dummy.DummyEmailBackend'``.

.. attribute:: PYMESS_EMAIL_BATCH_SENDING

  If you use standard SMTP service you should send e-mails in batches otherwise other SMTP providers could add your SMTP server to the black-list. With this setting you configure e-mail backend not to send e-mails directly but messages are only created in state "waiting". Finally e-mails should be sent with Django command ``send_emails_batch``. Default value is ``False``.

.. attribute:: PYMESS_EMAIL_BATCH_SIZE

  Defines maximum number of e-mails that are sent with command ``send_emails_batch``.

.. attribute:: PYMESS_EMAIL_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS

  Defines maximum number of attempts for sending one e-mail message. Default value is ``3``.

.. attribute:: PYMESS_EMAIL_BATCH_MAX_SECONDS_TO_SEND

  Defines maximum number of seconds to try to send an e-mail message that ended in an ``ERROR`` state. Default value is ``60 * 60`` (1 hour).

.. attribute:: PYMESS_EMAIL_MANDRILL

  Configuration of ``pymess.backend.email.mandrill.MandrillEmailBackend``.
