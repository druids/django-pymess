.. _dialer:

Dialer
======

Dialer messages that are stored inside Django model class defined later are sent via dialer backend. Currently there is one implementation of that backend `Daktela`. For sending dialer message you can use function ``pymess.backend.dialer.send`` or ``pymwess.backend.dialer.send_template``.

.. function:: pymess.backend.sms.send(recipient, content, related_objects=None, tag=None, **kwargs)

  Function has two required parameters ``recipient`` which is a phone number of the receiver and ``content``. Attribute ``content`` is a text message that will be read via 'text to speech' mechanism to the recipient. Attribute ``related_objects`` should contain a list of objects that you want to connect with the sent message (with generic relation). ``tag`` is string mark which is stored with the sent message. The last non required parameter ``**kwargs`` is extra data that will be stored inside dialer message model in field ``extra_data``.

.. function:: pymess.backend.dialer.send_template(recipient, slug, context_data, related_objects=None, tag=None)

  The second function is used for sending prepared templates that are stored inside template model (class that extends ``pymess.models.dialer.AbstractDialerTemplate``). The first parameter ``recipient`` is phone number of the receiver, ``slug`` is key of the template, ``context_data`` is a dictionary that contains context data for rendering dialer message content from the template, ``related_objects`` should contains list of objects that you want to connect with the sent message and  ``tag`` is string mark which is stored with the sent message.

Models
------

.. class:: pymess.models.dialer.DialerMessage

  The model contains data of already sent dialer messages.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: sent_at

    Django ``DateTimeField``, contains date and time of sending the message.

  .. attribute:: recipient

    ``CharField`` that contains phone number of the receiver.

  .. attribute:: content

    ``TextField``, contains content of the message.

  .. attribute:: template_slug

    If dialer message was sent from the template, this attribute contains key of the template.

  .. attribute:: template

    If dialer message was sent from the template, this attribute contains foreign key of the template. The reason why there is ``template_slug`` and ``template`` fields is that a template instance can be removed and it is good to keep at least the key of the template.

  .. attribute:: state

    Field contains the current state of the message. Allowed states are:

      * NOT_ASSIGNED - state of the message was not assigned yet
      * READY - the message is ready to be dialed to the recipient
      * RESCHEDULED_BY_DIALER - the call rescheduled by dialer service from any reason
      * CALL_IN_PROGRESS - recipient answered the call and message is being read
      * HANGUP - recipient hang up
      * DONE - message has been processed
      * RESCHEDULED - the call rescheduled by dialer service due to recipient action or state (hang up, not answering, unreachable, etc.)
      * ANSWERED_COMPLETE - recipient answered the call and listened up complete message
      * ANSWERED_PARTIAL - recipient answered the call and NOT listened up complete message
      * UNREACHABLE - recipient is unreachable
      * DECLINED - recipient declined to answer the call
      * UNANSWERED - recipient did not take any action
      * ERROR - error was raised during sending of the message
      * DEBUG - dialer message was not sent because system is in debug mode

  .. attribute:: backend

    Field contains path to the dialer backend that was used for sending of the message.

  .. attribute:: error

    If error was raised during sending of the dialer message this field contains text description of the error.

  .. attribute:: extra_data

    Extra data stored with ``JSONField``.

  .. attribute:: extra_sender_data

    Extra data related to the dialer backend stored with ``JSONField``. Every dialer backend can have different extra data.

  .. attribute:: tag

    String tag that you can define during sending dialer message.

  .. attribute:: is_final_state

    Helper field. If it cannot be resolved from message states clearly whether message is in its final state this field indicates it (based on further logic).

  .. attribute:: failed

    Returns ``True`` if message ended in ``ERROR`` state.

  .. attribute:: related_objects

    Returns DB manager of ``pymess.models.dialer.DialerMessageRelatedObject`` model that are related to the concrete dialer message.


.. class:: pymess.models.dialer.DialerMessageRelatedObject

  Model for storing related objects that you can connect with the dialer message.

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: dialer_message

    Foreign key to the dialer message.

  .. attribute:: content_type

    Content type of the stored model (generic relation)

  .. attribute:: object_id_int

    If a related objects has primary key in integer format the key is stored here. This field uses db index therefore filtering is much faster.

  .. attribute:: object_id

    Primary key of a related object stored in django ``TextField``.


.. class:: pymess.models.dialer.AbstractDialerTemplate

  Abstract class for dialer essage template which you can use to define your own dialer message template model. Your model that extends this class is set inside setting ``PYMESS_DIALER_TEMPLATE_MODEL``::

      PYMESS_DIALER_TEMPLATE_MODEL = 'your_application.YourDialerTemplateModel'

  .. attribute:: created_at

    Django ``DateTimeField``, contains date and time of creation.

  .. attribute:: changed_at

    Django ``DateTimeField``, contains date and time the of last change.

  .. attribute:: slug

    Key of the dialer message template in the string format (Django slug).

  .. attribute:: body

    Body of the dialer message. Final message content is rendered with Django template system by default.

  .. method:: get_body()

    Returns body of the model message. You can use it to update message body before rendering.

  .. method:: render_body(context_data)

    Renders template stored inside ``body`` field to the message content. Standard Django template system is used by default.

  .. method:: can_send(recipient, context_data)

    Returns by default ``True`` value. If you need to restrict sending dialer message template for some reasons, you can override this method.

  .. method:: send(recipient, context_data, related_objects=None, tag=None, **kwargs)

    Checks whether message can be sent, renders message content and sends it via defined backend. Finally, the sent message is returned. If message cannot be sent, ``None`` is returned.


.. class:: pymess.models.dialer.DialerTemplate

  Default template model class that only inherits from ``pymess.models.dialer.AbstractDialerTemplate``


Backends
--------

Backend is a class that is used for sending messages. Every backend must provide API defined by ``pymess.backends.dialer.DialerBackend`` class. Dialer backend is configured via ``PYMESS_DIALER_SENDER_BACKEND`` (ex. ``PYMESS_DIALER_SENDER_BACKEND = 'pymess.backend.dialer.daktela.DaktelaDialerBackend'``). There are currently implemented following SMS backends:

.. class:: pymess.backend.dialer.dummy.DummyDialerBackend

  Backend that can be used for testing. Dialer message is not sent. Instead, it is automatically set to the ``DEBUG`` state.

.. class:: pymess.backend.dialer.daktela.DaktelaDialerBackend

  Backend that uses Daktela API for sending dialer messages (https://www.daktela.com/api/v6/models/campaignsrecords)


Custom backend
^^^^^^^^^^^^^^

If you want to write your own Pymess dialer backend you must create class that inherits from ``pymess.backends.dialer.DialerBackend``::

.. class pymess.backend.dialer.daktela.DaktelaDialerBackend

  .. method:: publish_message(message)

    This method should send dialer message (obtained from the input argument) and update its state. This method must be overridden in the custom backend.

  .. method:: publish_messages(messages)

    If your service provides sending messages in batch you can override the ``publish_messages`` method. Input argument is a list of messages. By default, ``publish_message`` method is used for sending and messages are send one by one.

  .. method:: bulk_check_dialer_status()

    If your service provides checking message state you can override this method and implement code that check if dialer messages were delivered.

Commands
--------

Because some services provide checking whether dialer messages were delivered Pymess provides a command that calls backend method ``bulk_check_dialer_status``. You can use this command inside cron and periodically call it. But dialer backend and service must provide it (must have implemented method ``bulk_check_dialer_status``).
