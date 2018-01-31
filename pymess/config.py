from django.apps import apps
from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from attrdict import AttrDict


DEFAULTS = {
    'OUTPUT_SMS_MODEL': None,
    'SMS_TEMPLATE_MODEL': None,
    'ATS_SMS_CONFIG': {
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
    'SNS': {
    },
    'SMS_USE_ACCENT': False,
    'IDLE_SENDING_MESSAGES_TIMEOUT_MINUTES': 20,
    'LOG_IDLE_MESSAGES': True,
    'SET_ERROR_TO_IDLE_MESSAGES': True,
    'SMS_SENDER_BACKEND': None,
    'PUSH_SENDER_BACKEND': None,
    'SMS_DEFAULT_PHONE_CODE': None,
    'IDLE_MESSAGES_TIMEOUT_MINUTES': 10,
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


def get_output_sms_model():
    return apps.get_model(*settings.OUTPUT_SMS_MODEL.split('.'))


def get_sms_template_model():
    return apps.get_model(*settings.SMS_TEMPLATE_MODEL.split('.'))


def get_push_template_model():
    return apps.get_model(*settings.PUSH_TEMPLATE_MODEL.split('.'))


def get_push_notification_model():
    return apps.get_model(*settings.PUSH_NOTIFICATION_MODEL.split('.'))


def get_sms_sender():
    return import_string(settings.SMS_SENDER_BACKEND)()


def get_push_sender():
    return import_string(settings.PUSH_SENDER_BACKEND)()
