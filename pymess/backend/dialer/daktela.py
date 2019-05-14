from django.utils import timezone as tz
from django.utils.encoding import force_text

from pymess.backend.dialer import DialerBackend
from pymess.config import settings
from pymess.models import DialerMessage
from pymess.utils.logged_requests import generate_session


class DaktelaDialerBackend(DialerBackend):
    """
    Dialer backend implementing Daktela service https://www.daktela.com/api/v6/models/campaignsrecords
    """

    SESSION_SLUG = 'pymess-daktela_autodialer'

    @staticmethod
    def _get_dialer_api_url(name=None):
        name = '/{name}'.format(name=name) if name else ''

        return '{base_url}{name}.json?accessToken={access_token}'.format(
            base_url=settings.DIALER_DAKTELA.URL, name=name, access_token=settings.DIALER_DAKTELA.ACCESS_TOKEN,
        )

    def _update_dialer_states(self, messages):
        """
        Method uses Daktela API to get info about autodialer call status
        :param messages: list of dialer messages to update
        """
        for message in messages:
            name = message.extra_data['name']
            client_url = self._get_dialer_api_url(name)
            response = generate_session(
                slug=self.SESSION_SLUG,
                related_objects=(message,),
                timeout=self.DIALER_DAKTELA.TIMEOUT
            ).get(client_url)
            resp_json = response.json()

            message.extra_data.update({
                'name': name,
                'daktela_action': resp_json['result']['action'],
                'daktela_statuses': resp_json['result']['statuses'],
            })
            resp_message_state = resp_json['result']['statuses'][0]['name'] if len(
                resp_json['result']['statuses']) else resp_json['result']['action']
            custom_fields = resp_json['result']['customFields']
            tts_processed = custom_fields['ttsprocessed'][0]
            whole_message_heard = ('whole_message_heard' in custom_fields and custom_fields['whole_message_heard']
                                   and custom_fields['whole_message_heard'][0] == 'Yes')
            state_mapped = settings.DIALER_DAKTELA.STATES_MAPPING[resp_message_state]
            if state_mapped == DialerMessage.STATE.ANSWERED_PARTIAL and whole_message_heard:
                resp_message_state = str(DialerMessage.STATE.ANSWERED_COMPLETE)
            if state_mapped == DialerMessage.STATE.DONE and tts_processed == '0':
                resp_message_state = str(DialerMessage.STATE.NOT_ASSIGNED)
            message_state = settings.DIALER_DAKTELA.STATES_MAPPING[resp_message_state]
            message_error = resp_json['error'] if len(resp_json['error']) else None
            tts_processed = resp_json['result']['customFields']['ttsprocessed'][0]

            try:
                self.update_message(
                    message,
                    state=message_state,
                    error=message_error,
                    extra_data=message.extra_data,
                    is_final_state=resp_json['result']['action'] == '5' and tts_processed == '1',
                )
            except Exception as ex:
                self.update_message(message, state=DialerMessage.STATE.ERROR, error=force_text(ex))
                # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
                # and log them into database. Re-raise exception causes transaction rollback (lost of information about
                # exception).

    def publish_message(self, message):
        """
        Method uses Daktela API for sending dialer message
        :param message: dialer message
        """
        client_url = self._get_dialer_api_url()
        try:
            payload = {
                'queue': settings.DIALER_DAKTELA.QUEUE,
                'number': message.recipient,
                'customFields': {
                    'mall_pay_text': [
                        message.content,
                    ],
                    'ttsprocessed': [
                        0,
                    ],
                },
                'action': 5,
            }

            response = generate_session(
                slug=self.SESSION_SLUG,
                related_objects=(message,),
                timeout=self.DIALER_DAKTELA.TIMEOUT
            ).post(
                client_url,
                json=payload,
            )
            resp_json = response.json()

            message.extra_data.update({
                'name': resp_json['result']['name'],
                'daktela_action': resp_json['result']['action'],
                'daktela_statuses': resp_json['result']['statuses'],
            })

            self.update_message(
                message,
                state=DialerMessage.STATE.READY,
                error=resp_json['error'] if len(resp_json['error']) else None,
                sent_at=tz.now(),
                extra_data=message.extra_data,
            )
        except Exception as ex:
            self.update_message(message, state=DialerMessage.STATE.ERROR, error=force_text(ex))
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
