from http import HTTPStatus
from json.decoder import JSONDecodeError

import requests
from django.utils import timezone
from django.utils.encoding import force_text
from onesignal import DeviceNotification, OneSignalClient

from pymess.backend.push import PushNotificationBackend
from pymess.config import settings
from pymess.models import PushNotificationMessage
from pymess.utils.logged_requests import generate_session


class OneSignalPushNotificationBackend(PushNotificationBackend):

    def _is_result_partial_error(self, result):
        return not result.is_error and result.errors

    def _is_invalid_result(self, result):
        return result.is_error or self._is_result_partial_error(result)

    def publish_message(self, message):
        onesignal_client = OneSignalClient(settings.PUSH_NOTIFICATION_ONESIGNAL.APP_ID,
                                           settings.PUSH_NOTIFICATION_ONESIGNAL.API_KEY)
        onesignal_client.session = generate_session(
            slug='pymess - OneSignal',
            related_objects=(message,),
            timeout=settings.PUSH_NOTIFICATION_ONESIGNAL.TIMEOUT
        )

        languages = {'en'}
        if settings.PUSH_NOTIFICATION_ONESIGNAL.LANGUAGE is not None:
            languages.add(settings.PUSH_NOTIFICATION_ONESIGNAL.LANGUAGE)
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

            error_state, sent_state = PushNotificationMessage.STATE.ERROR_NOT_SENT, PushNotificationMessage.STATE.SENT
            if self._is_invalid_result(result):
                self.update_message_after_sending(
                    message,
                    state=error_state,
                    error=result.errors,
                    sent_at=timezone.now(),
                    extra_sender_data=extra_sender_data,
                    retry_sending=False
                )
            else:
                self.update_message_after_sending(
                    message,
                    state=sent_state,
                    sent_at=timezone.now(),
                    extra_sender_data=extra_sender_data,
                )
        except (JSONDecodeError, requests.exceptions.RequestException) as ex:
            self.update_message_after_sending(
                message, state=PushNotificationMessage.STATE.ERROR_NOT_SENT, error=force_text(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (loss of information
            # about exception).
