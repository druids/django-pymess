import re

from django.utils import timezone as tz
from django.utils.translation import ugettext as _

from pymess.backend.dialer import DialerBackend
from pymess.config import settings
from pymess.enums import DialerMessageState
from pymess.utils.logged_requests import generate_session


class DaktelaDialerBackend(DialerBackend):
    """
    Dialer backend implementing Daktela service https://www.daktela.com/api/v6/models/campaignsrecords
    """

    SESSION_SLUG = 'pymess-daktela_autodialer'
    config = {
        'ACCESS_TOKEN':  None,
        'AUTODIALER_RECORD_TYPE': None,
        'PREDICTIVE_RECORD_TYPE': None,
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
    }

    def _get_dialer_api_url(self, name=None):
        name = '/{name}'.format(name=name) if name else ''

        return '{base_url}{name}.json?accessToken={access_token}'.format(
            base_url=self.config['URL'], name=name, access_token=self.config['ACCESS_TOKEN'],
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
                timeout=self.config['TIMEOUT']
            ).get(client_url)
            resp_json = response.json()
            if response.status_code != 200 and resp_json.get('error'):
                self._update_message_state_with_error(message, error_message=resp_json.get('error'))
                continue

            message.extra_data.update({
                'name': name,
                'daktela_action': resp_json['result']['action'],
                'daktela_statuses': resp_json['result']['statuses'],
            })
            resp_message_state = resp_json['result']['statuses'][0]['name'] if len(
                resp_json['result']['statuses']) else resp_json['result']['action']
            state_mapped = self.config['STATES_MAPPING'][resp_message_state]
            message_error = resp_json['error'] if len(resp_json['error']) else None

            is_final_state = resp_json['result']['action'] == '5'

            try:
                self._update_message(
                    message,
                    state=state_mapped,
                    error=message_error,
                    extra_data=message.extra_data,
                    is_final_state=is_final_state,
                )
            except Exception as ex:
                self._update_message_state_with_error(message, error_message=ex)
                # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
                # and log them into database. Re-raise exception causes transaction rollback (lost of information about
                # exception).

    def _update_message_state_with_error(self, message, error_message):
        is_final_state = message.number_of_status_check_attempts >= settings.DIALER_NUMBER_OF_STATUS_CHECK_ATTEMPTS
        message_kwargs = {
            'state': DialerMessageState.ERROR_UPDATE,
            'error': ', '.join(error_message) if isinstance(error_message, list) else str(error_message),
            'is_final_state': is_final_state,
        }
        if not is_final_state:
            message_kwargs['number_of_status_check_attempts'] = message.number_of_status_check_attempts + 1
        self._update_message(
            message,
            **message_kwargs
        )

    def publish_message(self, message):
        """
        Method uses Daktela API for sending dialer message
        :param message: dialer message
        """
        client_url = self._get_dialer_api_url()
        try:
            payload = {
                'record_type': (
                    self.config['AUTODIALER_RECORD_TYPE'] if message.is_autodialer
                    else self.config['PREDICTIVE_RECORD_TYPE']
                ),
                'number': re.sub(r'^\+', '00', message.recipient),
                'customFields': {'autodialer_text': [message.content]},
            }
            custom_fields = message.extra_data.get('custom_fields')
            if custom_fields:
                payload['customFields'].update(**custom_fields)

            response = generate_session(
                slug=self.SESSION_SLUG,
                related_objects=(message,),
                timeout=self.config['TIMEOUT']
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

            error_message = resp_json.get('error')
            if error_message:
                self._update_message_after_sending_error(
                    message,
                    error=', '.join(error_message) if isinstance(error_message, list) else str(error_message),
                    state=DialerMessageState.ERROR
                )
            else:
                self._update_message_after_sending(
                    message,
                    state=DialerMessageState.READY,
                    sent_at=tz.now(),
                    extra_data=message.extra_data,
                )
        except Exception as ex:
            self._update_message_after_sending_error(
                message,
                error=str(ex)
            )
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
