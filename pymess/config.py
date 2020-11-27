from collections import OrderedDict
import re

from chamber.utils.datastructures import Enum
from django.apps import apps
from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from attrdict import AttrDict

DEFAULT_SENDER_BACKEND_NAME = 'default'

CONTROLLER_TYPES = Enum(
    'SMS',
    'EMAIL',
    'DIALER',
    'PUSH_NOTIFICATION',
)

DEFAULTS = {
    # SMS configuration
    'SMS_BACKENDS': {
        DEFAULT_SENDER_BACKEND_NAME: {
            'backend': 'pymess.backend.sms.dummy.DummySMSBackend'
        }
    },
    'SMS_DEFAULT_SENDER_BACKEND_NAME': DEFAULT_SENDER_BACKEND_NAME,
    'SMS_BACKEND_ROUTER': 'pymess.backend.routers.DefaultBackendRouter',
    'SMS_TEMPLATE_MODEL': 'pymess.SMSTemplate',
    'SMS_USE_ACCENT': False,
    'SMS_DEFAULT_PHONE_CODE': None,
    'SMS_LOG_IDLE_MESSAGES': True,
    'SMS_SET_ERROR_TO_IDLE_MESSAGES': True,
    'SMS_IDLE_MESSAGES_TIMEOUT_MINUTES': 10,
    'SMS_BATCH_SENDING': False,
    'SMS_BATCH_SIZE': 20,
    'SMS_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS': 3,
    'SMS_BATCH_MAX_SECONDS_TO_SEND': 60 * 60,
    'SMS_RETRY_SENDING': True,

    # E-mail configuration
    'EMAIL_BACKENDS': {
        DEFAULT_SENDER_BACKEND_NAME: {
            'backend': 'pymess.backend.emails.dummy.DummyEmailBackend'
        }
    },
    'EMAIL_DEFAULT_SENDER_BACKEND_NAME': DEFAULT_SENDER_BACKEND_NAME,
    'EMAIL_BACKEND_ROUTER': 'pymess.backend.routers.DefaultBackendRouter',
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
    'EMAIL_BATCH_SENDING': False,
    'EMAIL_BATCH_SIZE': 20,
    'EMAIL_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS': 3,
    'EMAIL_BATCH_MAX_SECONDS_TO_SEND': 60 * 60,
    'EMAIL_SENDERS': (),
    'EMAIL_HTML_DATA_DIRECTORY': None,
    'EMAIL_PULL_INFO_BATCH_SIZE': 100,
    'EMAIL_PULL_INFO_DELAY_SECONDS': 60 * 60,  # 1 hour
    'EMAIL_PULL_INFO_MAX_TIMEOUT_FROM_SENT_SECONDS': 60 * 60 * 24 * 30,  # 30 days
    'EMAIL_RETRY_SENDING': True,

    # Dialer configuration
    'DIALER_BACKENDS': {
        DEFAULT_SENDER_BACKEND_NAME: {
            'backend': 'pymess.backend.dialer.dummy.DummyDialerBackend'
        }
    },
    'DIALER_DEFAULT_SENDER_BACKEND_NAME': DEFAULT_SENDER_BACKEND_NAME,
    'DIALER_BACKEND_ROUTER': 'pymess.backend.routers.DefaultBackendRouter',
    'DIALER_TEMPLATE_MODEL': 'pymess.DialerTemplate',
    'DIALER_IDLE_MESSAGES_TIMEOUT_MINUTES': 60 * 24,
    'DIALER_NUMBER_OF_STATUS_CHECK_ATTEMPTS': 5,
    'DIALER_BATCH_SENDING': False,
    'DIALER_BATCH_SIZE': 20,
    'DIALER_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS': 3,
    'DIALER_BATCH_MAX_SECONDS_TO_SEND': 60 * 60,
    'DIALER_RETRY_SENDING': True,

    # Push notification settings
    'PUSH_NOTIFICATION_BACKENDS': {
        DEFAULT_SENDER_BACKEND_NAME: {
            'backend': 'pymess.backend.push.dummy.DummyPushNotificationBackend'
        }
    },
    'PUSH_NOTIFICATION_DEFAULT_SENDER_BACKEND_NAME': DEFAULT_SENDER_BACKEND_NAME,
    'PUSH_NOTIFICATION_BACKEND_ROUTER': 'pymess.backend.routers.DefaultBackendRouter',
    'PUSH_NOTIFICATION_TEMPLATE_MODEL': 'pymess.PushNotificationTemplate',
    'PUSH_NOTIFICATION_BATCH_SENDING': False,
    'PUSH_NOTIFICATION_BATCH_SIZE': 20,
    'PUSH_NOTIFICATION_BATCH_MAX_NUMBER_OF_SEND_ATTEMPTS': 3,
    'PUSH_NOTIFICATION_BATCH_MAX_SECONDS_TO_SEND': 60 * 60,
    'PUSH_NOTIFICATION_RETRY_SENDING': True,

    # General message settings
    'DEFAULT_MESSAGE_PRIORITY': 3,
}


class BackendNotFound(Exception):
    pass


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

def get_router(backend_type):
    router_option_name = '{}_BACKEND_ROUTER'.format(backend_type)
    return import_string(getattr(settings, router_option_name))()


def _get_backend_config_dict(backend_type):
    backends_option_name = '{}_BACKENDS'.format(backend_type)
    return getattr(settings, backends_option_name)


def get_backend(backend_type, backend_name):
    backend_from_config = _get_backend_config_dict(backend_type)[backend_name]
    return import_string(backend_from_config['backend'])(config=backend_from_config.get('config', {}))


def get_default_sender_backend_name(backend_type):
    backend_default_name = '{}_DEFAULT_SENDER_BACKEND_NAME'.format(backend_type)
    return getattr(settings, backend_default_name)


def get_supported_backend_paths(backend_type):
    return [backend_config_name['backend'] for backend_config_name in _get_backend_config_dict(backend_type)]


def get_dialer_template_model():
    """
    Function returns dialer template model defined in Pymess settings
    """
    return get_model(settings.DIALER_TEMPLATE_MODEL)


def get_push_notification_template_model():
    """
    Function returns push notification template model defined in Pymess settings
    """
    return get_model(settings.PUSH_NOTIFICATION_TEMPLATE_MODEL)


def is_turned_on_email_batch_sending():
    return settings.EMAIL_BATCH_SENDING


def is_turned_on_sms_batch_sending():
    return settings.SMS_BATCH_SENDING


def is_turned_on_push_notification_batch_sending():
    return settings.PUSH_NOTIFICATION_BATCH_SENDING


def is_turned_on_dialer_batch_sending():
    return settings.DIALER_BATCH_SENDING
