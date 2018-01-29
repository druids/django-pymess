.. _sms:

SMS
===

SMS messages that are stored inside Django model class defined later, are sent via SMS backend. There are implemented several SMS backends, every backed uses differend SMS service like twillio or AWS SNS. For sending SMS message you can use function ``pymess.backend.sms.send`` or ``pymwess.backend.sms.send_template``.

.. function:: send(recipient, content, **sms_attrs)

  Function has two required attributes ``recipient`` which is phone number of the receiver and ``content``. Attribute ``content`` is a text message that will be sent inside the SMS body. If setting ``PYMESS_SMS_USE_ACCENT`` is set to ``False``, accent in the content will be replaced by appropriate ascii characters. The last non required attribute ``**sms_attrs`` is extra data that will be stored inside SMS message model.

.. function:: send_template(recipient, slug, context)

  The second function is used for sending prepared templates that are stored inside template model (class that extends ``pymess.models.sms.AbstractSMSTemplate``). The first attribute ``recipient`` is phone number of the receiver, ``slug`` is key of the template and ``context`` is a dictionary that contains context data for rendering SMS content from the template.

Models
------

As mentioned above there are two abstract Django model classes that you must extend to use Pymess library for sending SMS messages ``pymess.models.sms.AbstractSMSMessage`` and ``pymess.models.sms.AbstractSMSTemplate``.

.. class:: pymess.models.sms.AbstractSMSMessage

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: sent_at

    Django ``DateTimeField``, contains date and time of sending the SMS message.

  .. attribute:: recipient

    ``CharField`` that contains phone number of the receiver.

  .. attribute:: sender

    ``CharField`` that contains phone number of the sender. Field can be empty if backend doesn't provide sender number.

  .. attribute:: content

    ``TextField``, contains content of the SMS message.

  .. attribute:: template_slug

    If SMS was sent from the template, this attribute cointains key of the template.

  .. attribute:: template

    If SMS was sent from the template, this attribute contains foreign key of the template. The reason why there is ``template_slug`` and ``template`` fields is that a template instance can be removed and it is good to keep at least the key of the template.

  .. attribute:: state

    Field contains the current state of the message. Allowed states are:

      * WAITING - SMS was not sent to the external service
      * UNKNOWN - SMS was sent to the external service but its state is unknown
      * SENDING - SMS was sent to the external service
      * SENT - SMS was sent to the receiver
      * ERROR - error was raised during sending of the SMS message
      * DEBUG - SMS was not sent because system is in debug mode
      * DELIVERED - SMS was delivered to the receiver

  .. attribute:: backend

    Field contains path to the SMS backend that was used for sending of the SMS message.

  .. attribute:: error

    If error was raised during sending of the SMS message this field contains text description of the error.

  .. attirubte:: extra_data

    Extra data stored inside ``JSONField``. Every SMS backend can have different extra data.

  .. property:: failed

    Returns ``True`` if SMS ended in ``ERROR`` state.


Your model that extends this class is set inside setting ``PYMESS_OUTPUT_SMS_MODEL``::

    PYMESS_OUTPUT_SMS_MODEL = 'your_application.YourSMSMessageModel'


.. class:: pymess.models.sms.AbstractSMSTemplate

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: slug

    Key of the SMS template in the string format (Django slug).

  .. attribute:: body

    Body of the SMS message. Final SMS content is rendered with Django template system by default.

  .. method:: render(recipient, context)

    Method that renders template stored inside ``body`` field to the message content. Standard Django template system is used by default.

  .. method:: can_send(recipient, context)

    Method that returns by default ``True`` value. If you need to restrict sending SMS template for some reasons, you can override this method.

  .. method:: send(recipient, context)

    Method that checks if message can be sent, renders message content and sends it via defined backend. Finally, the sent message is returned. If message cannot be sent, ``None`` is returned.

Your model that extends this class is set inside setting ``PYMESS_OUTPUT_SMS_MODEL``::

    PYMESS_SMS_TEMPLATE_MODEL = 'your_application.YourSMSTemplateModel'

Backends
--------

Backend is a class that is used for sending messages. Every backend must provide API defined by ``pymess.backends.sms.SMSBackend`` class. SMS backend is configured via ``PYMESS_SMS_SENDER_BACKEND`` (ex. ``SMS_SENDER_BACKEND = 'pymess.backend.sms.sns.SNSSMSBackend'``). There are currently implemented following SMS backends:

.. class:: pymess.backend.dummy.DummySMSBackend

  Backend that can be used for testing. SMS is not sent, but is automatically set to the ``DEBUG`` state.

.. class:: pymess.backend.sns.SNSSMSBackend

  Backend that uses amazon SNS for sending messages (https://aws.amazon.com/sns/)

.. class:: pymess.backend.twilio.TwilioSMSBackend

  Backend that uses twilio service for sending SMS messages (https://www.twilio.com/)

.. class:: pymess.backend.ats_sms_operator.ATSSMSBackend

  Czech ATS SMS service is used for sending SMS messages. Service and backend supports checking if SMS was actually delivered. (https://www.atspraha.cz/)

  Configuration of attributes according to ATS operator documentation::

    PYMESS_ATS_SMS_CONFIG = {
        'URL': 'http://fik.atspraha.cz/gwfcgi/XMLServerWrapper.fcgi',  # If you use default URL param, this doesn't need to be set
        'UNIQ_PREFIX': 'unique-id-prefix',  # If you use SMS service for more applications you can define this prefix and it will be added to the message ID
        'USERNAME': 'username',
        'PASSWORD': 'password',
        'UNIQ_PREFIX': '',
        'VALIDITY': 60,
        'TEXTID': None,
        'OPTID': '',
    }

.. class:: pymess.backend.sms_operator.SMSOperatorBackend

  Czech SMS operator service is used for sending SMS messages. Service and backend supports checking if SMS was actually delivered. (https://www.sms-operator.cz/)

  Configuration of attributes according to SMS operator documentation::

    PYMESS_SMS_OPERATOR_CONFIG = {
        'URL': 'https://www.sms-operator.cz/webservices/webservice.aspx',  # If you use default URL param, this doesn't need to be set
        'UNIQ_PREFIX': 'unique-id-prefix',  # If you uses SMS service for more applications you can define this prefix and it will be added to the message ID
         'USERNAME': 'username',
         'PASSWORD': 'password',
    }


Custom backend
^^^^^^^^^^^^^^

If you want to write your own Pymess SMS backend, you must create class that inherits from ``pymess.backends.sms.SMSBackend``::

.. class pymess.backends.sms.SMSBackend

  .. attribute:: name

    Unique string name of the SMS backend. You must define this value for your backend.

  .. method:: publish_message(message)

    This method should send SMS message (obtained from the input argument) and update its state. This method must be overridden in the custom backend.

  .. method:: publish_messages(messages)

    If your service that provides sending messages in batch, you can override the ``publish_messages`` method. Input argument is a list of messages. By default, ``publish_message`` method is used for sending and messages are send one by one.

  .. method:: bulk_check_sms_states()

    If your service provides checking SMS state you can override this method and implement code that check if SMS messages were delivered.

Commands
--------

Because some services provide checking if SMS messages were delivered, Pymess provides a command that calls backend method ``bulk_check_sms_state``. You can use this command inside cron and periodically call it. But SMS backend and service must provide it (must have implemented method ``bulk_check_sms_states``).
