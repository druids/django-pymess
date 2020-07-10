.. _push:

Push notifications
==================

PUSH notifications are stored inside Django model class defined later, are sent via push notifications backend. There are implemented only one push notification backend ``pymess.backend.push.onesignal``.

.. function:: pymess.backend.push.send(recipient, content, related_objects=None, tag=None, **push_nofification_kwargs)

  Function has two required parameters ``recipient`` which is an identifier of the receiver and ``content``. Attribute ``content`` is a text message that will be sent inside the push notification. Attribute ``related_objects`` should contain a list of objects that you want to connect with the sent message (with generic relation). ``tag`` is string mark which is stored with the sent message . The last non required parameter ``**push_nofification_kwargs`` is extra data that will be stored inside push notification model in field ``extra_data``.

.. function:: pymess.backend.push.send_template(recipient, slug, context_data, related_objects=None, tag=None)

  The second function is used for sending prepared templates that are stored inside template model (class that extends ``pymess.models.push.AbstractPushNotificationTemplate``). The first parameter ``recipient`` is identifier of the receiver, ``slug`` is key of the template, ``context_data`` is a dictionary that contains context data for rendering push notification content from the template, ``related_objects`` should contains list of objects that you want to connect with the sent message and  ``tag`` is string mark which is stored with the sent push notification message.

Models
------


.. class:: pymess.models.push.PushNotificationMessage

  The model contains data of already sent push messages.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: sent_at

    Django ``DateTimeField``, contains date and time of sending the push message.

  .. attribute:: recipient

    ``CharField`` that contains identifier of the receiver.

  .. attribute:: content

    ``TextField``, contains content of the push message.

  .. attribute:: heading

    ``TextField``, heading of the push message.

  .. attribute:: url

    ``URLField``, URL link of th push message

  .. attribute:: template_slug

    If push was sent from the template, this attribute cointains key of the template.

  .. attribute:: template

    If push was sent from the template, this attribute contains foreign key of the template. The reason why there is ``template_slug`` and ``template`` fields is that a template instance can be removed and it is good to keep at least the key of the template.

  .. attribute:: state

    Field contains the current state of the message. Allowed states are:

      * DEBUG - Push notification was not sent because system is in debug mode
      * ERROR - Push notification was raised during sending of the message
      * ERROR_RETRY - error was raised during sending of the message, message will be retried
      * SENT - Push notification was sent to the receiver
      * WAITING - Push notification was not sent to the external service

  .. attribute:: backend

    Field contains path to the push backend that was used for sending of the push notifiaction.

  .. attribute:: error

    If error was raised during sending of the push notifiaction this field contains text description of the error.

  .. attribute:: extra_data

    Extra data stored with ``JSONField``.

  .. attribute:: extra_sender_data

    Extra data related to the backend stored with ``JSONField``. Every backend can have different extra data.

  .. attribute:: tag

    String tag that you can define during sending message.

  .. attribute:: number_of_send_attempts

    Number of sending attempts. Value is set only when batch sending is used.

  .. attribute:: retry_sending

    Defines if message should be resent if sending failed.

  .. attribute:: related_objects

    Returns DB manager of ``pymess.models.push.PushNotificationRelatedObject`` model that are related to the concrete message.


.. class:: pymess.models.sms.PushNotificationRelatedObject

  Model for storing related objects that you can connect with the push message.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: output_sms_message

    Foreign key to the push message.

  .. attribute:: content_type

    Content type of the stored model (generic relation)

  .. attribute:: object_id

    Primary key of a related object stored in django ``TextField``.


.. class:: pymess.models.sms.AbstractPushNotificationTemplate

  Abstract class of push notification template which you can use to define your own template model. Your model that extends this class is set inside setting ``PYMESS_PUSH_NOTIFICATION_TEMPLATE_MODEL``::

      PYMESS_PUSH_NOTIFICATION_TEMPLATE_MODEL = 'your_application.YourPushTemplateModel'

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: slug

    Key of the push template in the string format (Django slug).

  .. attribute:: body

    Body of the push message. Final push content is rendered with Django template system by default.

  .. attribute:: is_active

    Sets whether the template is active and should be sent or not.

  .. method:: get_body()

    Returns body of the model message. You can use it to update push body before rendering.

  .. method:: render_body(context_data)

    Renders template stored inside ``body`` field to the message content. Standard Django template system is used by default.

  .. method:: can_send(recipient, context_data)

    Returns by default the value of ``is_active``. If you need to restrict sending push notification template for some reasons, you can override this method.

  .. method:: send(recipient, context_data, related_objects=None, tag=None)

    Checks if message can be sent, renders message content and sends it via defined backend. Finally, the sent message is returned. If message cannot be sent, ``None`` is returned.


.. class:: pymess.models.sms.PushNotificationTemplate

  Default template model class that only inherits from ``pymess.models.push.PushNotificationTemplate``


Backends
--------

Backend is a class that is used for sending messages. Every backend must provide API defined by ``pymess.backends.push.PushNotificationBackend`` class. Push notification backend is configured via ``PYMESS_PUSH_NOTIFICATION_SENDER_BACKEND``:

.. class:: pymess.backend.push.dummy.DummyPushNotificationBackend

  Backend that can be used for testing. Message is not sent, but is automatically set to the ``DEBUG`` state.

.. class:: pymess.backend.push.onesignal.OneSignalPushNotificationBackend

  Backend that uses OneSignal for sending push notification (https://app.onesignal.com/)

  Configuration of attributes according to push notification operator documentation::

    PYMESS_PUSH_NOTIFICATION_ONESIGNAL = {
        'APP_ID': 'app-id',
        'API_KEY': 'api-key,
        'LANGUAGE': 'language',
    }


Commands
--------

``send_messages_batch``
^^^^^^^^^^^^^^^^^^^^^^^

As mentioned push notifications can be sent in a batch with Django command ``send_messages_batch --type=push-notification``.