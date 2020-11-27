from attrdict import AttrDict
from http import HTTPStatus
from json.decoder import JSONDecodeError

import requests
from django.utils import timezone
from onesignal import DeviceNotification, OneSignalClient
from onesignal.errors import OneSignalAPIError

from pymess.backend.push import PushNotificationBackend
from pymess.config import settings
from pymess.models import PushNotificationMessage
from pymess.utils.logged_requests import generate_session


class OneSignalPushNotificationBackend(PushNotificationBackend):

    config = AttrDict({
        'APP_ID': None,
        'API_KEY': None,
        'LANGUAGE': None,
        'TIMEOUT': 5,  # 5s
    })

    def _is_result_partial_error(self, result):
        return not result.is_error and result.errors

    def _is_invalid_result(self, result):
        return result.is_error or self._is_result_partial_error(result)

    def publish_message(self, message):
        onesignal_client = OneSignalClient(self.config.APP_ID,
                                           self.config.API_KEY)
        onesignal_client.session = generate_session(
            slug='pymess - OneSignal',
            related_objects=(message,),
            timeout=self.config.TIMEOUT
        )

        languages = {'en'}
        if self.config.LANGUAGE is not None:
            languages.add(self.config.LANGUAGE)
        notification = DeviceNotification(
            include_external_user_ids=(message.recipient,),
            contents={language: message.content for language in languages},
            headings={language: message.heading for language in languages},
            data=message.extra_data,
            url=message.url,
        )

        try:
            result = onesignal_client.send(notification)

            extra_sender_data = message.extra_sender_data or {}
            extra_sender_data['result'] = result.body

            if self._is_invalid_result(result):
                self._update_message_after_sending_error(
                    message,
                    state=PushNotificationMessage.STATE.ERROR,
                    error=str(result.errors),
                    extra_sender_data=extra_sender_data,
                )
            else:
                self._update_message_after_sending(
                    message,
                    state=PushNotificationMessage.STATE.SENT,
                    sent_at=timezone.now(),
                    extra_sender_data=extra_sender_data,
                )
        except (JSONDecodeError, requests.exceptions.RequestException, OneSignalAPIError) as ex:
            self._update_message_after_sending_error(
                message, error=str(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (loss of information
            # about exception).
