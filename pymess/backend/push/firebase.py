from django.conf import settings
from django.utils.encoding import force_text

from chamber.shortcuts import change_and_save

from pymess import config
from pymess.backend.push import PushBackend
from pymess.models import AbstractPushNotification

from pyfcm import FCMNotification


class FirebasePushBackend(PushBackend):

    name = 'firebase'

    def _publish_message(self, message):
        client = FCMNotification(api_key=settings.FIREBASE_API_KEY)
        result = client.notify_single_device(
            registration_id=message.user_device.registration_id,
            message_title=config.PYMESS_SENDER_ID,
            message_body=message.content,
            data_message={
                'slug': message.template_slug,
            }
        )
        try:
            if 'error' in result['results'][0]:
                change_and_save(message, state=AbstractPushNotification.STATE.ERROR,
                                error=result['results'][0]['error'])
            else:
                change_and_save(message, state=AbstractPushNotification.STATE.SENT)
        except Exception as ex:
            change_and_save(message, state=AbstractPushNotification.STATE.ERROR,
                            error=force_text(ex))
