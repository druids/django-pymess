.. _installation:

Installation
============

Using PIP
---------

Django pyston is not currently inside *PyPE* but in the future you will be able to use:

.. code-block:: console

    $ pip install django-pymess


Because *django-pymess* is rapidly evolving framework the best way how to install it is use source from github

.. code-block:: console

    $ pip install https://github.com/druids/django-pymess/tarball/{{ version }}#egg=django-pymess-{{ version }}

Configuration
=============

After installation you must go through these steps:

Required Settings
-----------------

The following variables have to be added to or edited in the project's ``settings.py``:

For using pymess you just add add ``pymess`` to ``INSTALLED_APPS`` variable::

    INSTALLED_APPS = (
        ...
        'pymess',
        ...
    )

Setup
-----

.. attribute:: PYMESS_OUTPUT_SMS_MODEL

  Setting Django model of SMS message. Pymess only defines abstract model class of SMS message ``pymess.models.sms.AbstractOutputSMSMessage`` you must inherit this model and sets the setting that references a custom SMS model:

.. attribute:: PYMESS_SMS_TEMPLATE_MODEL

  Similarly to ``PYMESS_OUTPUT_SMS_MODEL`` setting if you can use SMS templates you must set this settings wwithou your custom SMS template model that extends ``pymess.models.sms.AbstractSMSTemplate``.

.. attribute:: PYMESS_SMS_USE_ACCENT

  Setting that sets if SMS will be send with accent or not. Default value is ``False``.

.. attribute:: PYMESS_LOG_IDLE_MESSAGES

  Setting that sets whether the delivery time is checked for messages. Default value is ``True``.

.. attribute:: PYMESS_IDLE_SENDING_MESSAGES_TIMEOUT_MINUTES

  If setting ``PYMESS_LOG_IDLE_MESSAGES`` is set to ``True`` ``PYMESS_IDLE_SENDING_MESSAGES_TIMEOUT_MINUTES`` defines the number of minutes to send a warning that sms has not been sent. Default value is ``10``.

.. attribute:: PYMESS_SMS_DEFAULT_PHONE_CODE

  Country code that is set to the recipient if phone number doesn't contain another one.

.. attribute:: PYMESS_SMS_SENDER_BACKEND

  Path to the SMS backend that will be used for sending SMS messages.

.. attribute:: PYMESS_ATS_SMS_CONFIG

  Configuration of ``pymess.backend.sms.ats_sms_operator.ATSSMSBackend``.

.. attribute:: PYMESS_SMS_OPERATOR_CONFIG

  Configuration of ``pymess.backend.sms.sms_operator.SMSOperatorBackend``.

