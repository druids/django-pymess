from django.apps import apps
from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from attrdict import AttrDict


DEFAULTS = {
    # SMS configuration
    'SMS_TEMPLATE_MODEL': 'pymess.SMSTemplate',
    'SMS_ATS_CONFIG': {
        'UNIQ_PREFIX': 'test',
        'VALIDITY': 60,
        'TEXTID': None,
        'URL': 'http://fik.atspraha.cz/gwfcgi/XMLServerWrapper.fcgi',
        'OPTID': '',
    },
    'SMS_OPERATOR_CONFIG': {
        'URL': 'https://www.sms-operator.cz/webservices/webservice.aspx',
        'UNIQ_PREFIX': 'test',
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
    },
    'EMAIL_BATCH_SENDING': False,
    'EMAIL_BATCH_LOCK_FILE': 'pymess_send_batch_emails',
    'EMAIL_BATCH_LOCK_WAIT_TIMEOUT': -1,
    'EMAIL_BATCH_SIZE': 20,
    'EMAIL_SENDERS': (),
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
