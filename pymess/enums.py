from django.utils.translation import ugettext_lazy as _

from enumfields import IntegerChoicesEnum


class DialerMessageState(IntegerChoicesEnum):
     # numbers are matching predefined state values in Daktela

     WAITING = -1, _('waiting')
     NOT_ASSIGNED = 0, _('not assigned')
     READY = 1, _('ready')
     RESCHEDULED_BY_DIALER = 2, _('rescheduled by dialer')
     CALL_IN_PROGRESS = 3, _('call in progress')
     HANGUP = 4, _('hangup')
     DONE = 5, _('done')
     RESCHEDULED = 6, _('rescheduled')
     ANSWERED_COMPLETE = 7, _('listened up complete message')
     ANSWERED_PARTIAL = 8, _('listened up partial message')
     UNREACHABLE = 9, _('unreachable')
     DECLINED = 10, _('declined')
     UNANSWERED = 11, _('unanswered')
     HANGUP_BY_DIALER = 12, _('unanswered - hangup by dialer')
     HANGUP_BY_CUSTOMER = 13, _('answered - hangup by customer')
     ERROR_UPDATE = 66, _('error message update')
     DEBUG = 77, _('debug')
     ERROR = 88, _('error')
     ERROR_RETRY = 99, _('error retry')


class EmailMessageState(IntegerChoicesEnum):

    WAITING = 1, _('waiting')
    SENDING = 2, _('sending')
    SENT = 3, _('sent')
    ERROR = 4, _('error')
    DEBUG = 5, _('debug')
    ERROR_RETRY = 6, _('error retry')


class PushNotificationMessageState(IntegerChoicesEnum):

    WAITING = 1, _('waiting')
    SENT = 2, _('sent')
    ERROR = 3, _('error')
    DEBUG = 4, _('debug')
    ERROR_RETRY = 5, _('error retry')


class OutputSMSMessageState(IntegerChoicesEnum):

    WAITING = 1, _('waiting')
    UNKNOWN = 2, _('unknown')
    SENDING = 3, _('sending')
    SENT = 4, _('sent')
    ERROR_UPDATE = 5, _('error message update')
    DEBUG = 6, _('debug')
    DELIVERED = 7, _('delivered')
    ERROR = 8, _('error')
    ERROR_RETRY = 9, _('error retry')
