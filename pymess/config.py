from django.apps import apps
from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from attrdict import AttrDict


DEFAULTS = {
    # SMS configuration
    'SMS_TEMPLATE_MODEL': 'pymess.SMSTemplate',
    'SMS_ATS_CONFIG': {
        'UNIQ_PREFIX': '',
        'VALIDITY': 60,
        'TEXTID': None,
        'URL': 'http://fik.atspraha.cz/gwfcgi/XMLServerWrapper.fcgi',
        'OPTID': '',
        'TIMEOUT': 5,  # 5s
    },
    'SMS_OPERATOR_CONFIG': {
        'URL': 'https://www.sms-operator.cz/webservices/webservice.aspx',
        'UNIQ_PREFIX': '',
        'TIMEOUT': 5,  # 5s
    },
    'SMS_SNS_CONFIG': {
    },
    'SMS_USE_ACCENT': False,
    'SMS_DEFAULT_PHONE_CODE': None,
    'SMS_SENDER_BACKEND': 'pymess.backend.sms.dummy.DummySMSBackend',
    'SMS_LOG_IDLE_MESSAGES': True,
    'SMS_SET_ERROR_TO_IDLE_MESSAGES': True,
    'SMS_IDLE_MESSAGES_TIMEOUT_MINUTES': 10,

    # E-mail configuration
    'EMAIL_TEMPLATE_MODEL': 'pymess.EmailTemplate',
    'EMAIL_TEMPLATE_BASE_TEMPLATE': None,
    'EMAIL_TEMPLATE_TEMPLATETAGS': ['pymess'],
    'EMAIL_TEMPLATE_CONTENT_BLOCK': 'email_content',
    'EMAIL_TEMPLATE_CONTEXT_PROCESSORS': None,
    'EMAIL_TEMPLATE_EXTEND_BODY': True,
    'EMAIL_TEMPLATE_BANNED_TAGS': (
        'applet',
        'amp-iframe',
        'canvas',
        'embed',
        'noscript',
        'object',
        'script',
        'video',
    ),
    'EMAIL_SENDER_BACKEND': 'pymess.backend.emails.dummy.DummyEmailBackend',
    'EMAIL_MANDRILL': {
        'HEADERS': None,
        'TRACK_OPENS': False,
        'TRACK_CLICKS': False,
        'AUTO_TEXT': False,
        'INLINE_CSS': False,
        'URL_STRIP_QS': False,
        'PRESERVE_RECIPIENTS': False,
        'VIEW_CONTENT_LINK': True,
        'ASYNC': False,
        'TIMEOUT': 5,  # 5s
    },
    'EMAIL_BATCH_SENDING': False,
    'EMAIL_BATCH_LOCK_FILE': 'pymess_send_batch_emails',
    'EMAIL_BATCH_LOCK_WAIT_TIMEOUT': -1,
    'EMAIL_BATCH_SIZE': 20,
    'EMAIL_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS': 3,
    'EMAIL_BATCH_MAX_SECONDS_TO_SEND': 60 * 60,
    'EMAIL_SENDERS': (),
    'EMAIL_HTML_DATA_DIRECTORY': None,

    # Dialer configuration
    'DIALER_TEMPLATE_MODEL': 'pymess.DialerTemplate',
    'DIALER_SENDER_BACKEND': 'pymess.backend.dialer.dummy.DummyDialerBackend',
    'DIALER_DAKTELA': {
        'ACCESS_TOKEN':  None,
        'QUEUE': None,
        'URL': None,
        'STATES_MAPPING': {
            '0': 0,
            '1': 1,
            '2': 2,
            '3': 3,
            '4': 4,
            '5': 5,
            '6': 6,
        },
        'TIMEOUT': 5,  # 5s
    },
    'DIALER_IDLE_MESSAGES_TIMEOUT_MINUTES': 60 * 24,

    # Push notification settings
    'PUSH_NOTIFICATION_TEMPLATE_MODEL': 'pymess.PushNotificationTemplate',
    'PUSH_NOTIFICATION_SENDER_BACKEND': 'pymess.backend.push.dummy.DummyPushNotificationBackend',
    'PUSH_NOTIFICATION_ONESIGNAL': {
        'APP_ID': None,
        'API_KEY': None,
        'LANGUAGE': None,
        'TIMEOUT': 5,  # 5s
    },
}


class Settings(object):
    """
    Pymess settings is loaded lazy like Django settings.
    The reason is usability of override_settings decorator with tests
    """

    def __getattr__(self, attr):
        if attr not in DEFAULTS:
            raise AttributeError('Invalid Pymess setting: "{}"'.format(attr))

        default_value = DEFAULTS[attr]
        value = getattr(django_settings, 'PYMESS_{}'.format(attr), DEFAULTS[attr])

        if isinstance(default_value, dict) and isinstance(value, dict):
            default_value = default_value.copy()
            default_value.update(value)
            value = AttrDict(default_value)

        return value


settings = Settings()


def get_model(model_name):
    """
    Helper that returns django model class defined by string {app_label}.{model_name}
    """
    return apps.get_model(*model_name.split('.'))


def get_sms_template_model():
    """
    Function returns SMS template model defined in Pymess settings
    """
    return get_model(settings.SMS_TEMPLATE_MODEL)


def get_email_template_model():
    """
    Function returns e-mail template model defined in Pymess settings
    """
    return get_model(settings.EMAIL_TEMPLATE_MODEL)


def get_sms_sender():
    """
    Function returns SMS sender backend from string defined in Pymess settings
    """
    return import_string(settings.SMS_SENDER_BACKEND)()


def get_email_sender():
    """
    Function returns e-mail sender backend from string defined in Pymess settings
    """
    return import_string(settings.EMAIL_SENDER_BACKEND)()


def get_dialer_template_model():
    """
    Function returns dialer template model defined in Pymess settings
    """
    return get_model(settings.DIALER_TEMPLATE_MODEL)


def get_dialer_sender():
    """
    Function returns dialer sender backend from string defined in Pymess settings
    """
    return import_string(settings.DIALER_SENDER_BACKEND)()


def get_push_notification_template_model():
    """
    Function returns push notification template model defined in Pymess settings
    """
    return get_model(settings.PUSH_NOTIFICATION_TEMPLATE_MODEL)


def get_push_notification_sender():
    """
    Function returns push notification sender backend from string defined in Pymess settings
    """
    return import_string(settings.PUSH_NOTIFICATION_SENDER_BACKEND)()
