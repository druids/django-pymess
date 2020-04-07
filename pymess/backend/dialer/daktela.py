import re

from chamber.exceptions import PersistenceException
from django.utils import timezone as tz
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

from pymess.backend.dialer import DialerBackend, DialerSendingError
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

    def _get_autodialer_message_states(self, resp_json, state_mapped, resp_message_state):
        custom_fields = resp_json['result']['customFields']
        tts_processed = custom_fields['ttsprocessed'][0]
        whole_message_heard = ('whole_message_heard' in custom_fields and custom_fields['whole_message_heard']
                               and custom_fields['whole_message_heard'][0] == 'Yes')
        if state_mapped == DialerMessage.STATE.ANSWERED_PARTIAL and whole_message_heard:
            resp_message_state = str(DialerMessage.STATE.ANSWERED_COMPLETE)
        if state_mapped == DialerMessage.STATE.DONE and tts_processed == '0':
            resp_message_state = str(DialerMessage.STATE.NOT_ASSIGNED)
        tts_processed = resp_json['result']['customFields']['ttsprocessed'][0]
        is_final_state = resp_json['result']['action'] == '5' and tts_processed == '1'
        message_state = settings.DIALER_DAKTELA.STATES_MAPPING[resp_message_state]
        return is_final_state, message_state

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
                timeout=settings.DIALER_DAKTELA.TIMEOUT
            ).get(client_url)
            resp_json = response.json()
            if response.status_code != 200 and resp_json.get('error'):
                self._update_message_with_error(message, error_message=resp_json.get('error'), is_final_state=False)
                continue

            message.extra_data.update({
                'name': name,
                'daktela_action': resp_json['result']['action'],
                'daktela_statuses': resp_json['result']['statuses'],
            })
            resp_message_state = resp_json['result']['statuses'][0]['name'] if len(
                resp_json['result']['statuses']) else resp_json['result']['action']
            state_mapped = settings.DIALER_DAKTELA.STATES_MAPPING[resp_message_state]
            message_error = resp_json['error'] if len(resp_json['error']) else None

            if message.is_autodialer:
                is_final_state, message_state = self._get_autodialer_message_states(resp_json, state_mapped,
                                                                                    resp_message_state)
            else:
                message_state = state_mapped
                is_final_state = resp_json['result']['action'] == '5'

            try:
                self.update_message(
                    message,
                    state=message_state,
                    error=message_error,
                    extra_data=message.extra_data,
                    is_final_state=is_final_state,
                )
            except Exception as ex:
                self._update_message_with_error(message, error_message=ex, is_final_state=False)
                # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
                # and log them into database. Re-raise exception causes transaction rollback (lost of information about
                # exception).

    def _update_message_with_error(self, message, error_message, state=DialerMessage.STATE.ERROR_UPDATE,
                                   is_sending=False, is_final_state=True):
        status_check_attempt_remaining_exceeded = (
            True if message.number_of_status_check_attempts >= settings.DIALER_NUMBER_OF_STATUS_CHECK_ATTEMPTS
            else is_final_state
        )
        message_kwargs = {
            'state': state,
            'error': ', '.join(error_message) if isinstance(error_message, list) else str(error_message),
            'is_final_state': status_check_attempt_remaining_exceeded,
        }
        if not status_check_attempt_remaining_exceeded:
            message_kwargs['number_of_status_check_attempts'] = message.number_of_status_check_attempts + 1
        if is_sending:
            self.update_message_after_sending(
                message,
                **message_kwargs
            )
        else:
            self.update_message(
                message,
                **message_kwargs
            )

    def publish_message(self, message):
        """
        Method uses Daktela API for sending dialer message
        :param message: dialer message
        """
        client_url = self._get_dialer_api_url()
        testing_phones = settings.DIALER_DAKTELA.TESTING_PHONES
        if testing_phones and message.recipient not in testing_phones:
            error_message = _('Not allowed number to dial. Allowed numbers are: {}').format(', '.join(testing_phones))
            self._update_message_with_error(message, error_message, state=DialerMessage.STATE.DEBUG)
            return
        try:
            payload = {
                'queue': (settings.DIALER_DAKTELA.AUTODIALER_QUEUE if message.is_autodialer
                          else settings.DIALER_DAKTELA.PREDICTIVE_QUEUE),
                'number': re.sub(r'^\+', '00', message.recipient),
                'customFields': {
                    'mall_pay_text': [
                        message.content,
                    ],
                    'ttsprocessed': [
                        0,
                    ],
                },
            }
            if message.is_autodialer:
                payload['action'] = 5
            custom_fields = message.extra_data.get('custom_fields')
            if custom_fields:
                payload['customFields'].update(**custom_fields)

            response = generate_session(
                slug=self.SESSION_SLUG,
                related_objects=(message,),
                timeout=settings.DIALER_DAKTELA.TIMEOUT
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
                self._update_message_with_error(
                    message,
                    error_message,
                    state=DialerMessage.STATE.ERROR_NOT_SENT,
                    is_sending=True,
                    retry_sending=False,
                    is_final_state=False,
                )
            else:
                self.update_message_after_sending(
                    message,
                    state=DialerMessage.STATE.READY,
                    sent_at=tz.now(),
                    extra_data=message.extra_data,
                )
        except Exception as ex:
            self._update_message_with_error(
                message,
                ex,
                state=DialerMessage.STATE.ERROR_NOT_SENT,
                is_sending=True,
                is_final_state=False
            )
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).

    def create_message(self, recipient, content=None, related_objects=None, tag=None, template=None,
                       is_autodialer=True, **kwargs):
        """
        Create dialer message which will be logged in the database (content is not needed for this .
        :param recipient: phone number of the recipient
        :param related_objects: list of related objects that will be linked with the dialer message using generic
        relation
        :param tag: string mark that will be saved with the message
        :param kwargs: extra attributes that will be saved with the message
        """
        try:
            return super().create_message(
                recipient=recipient,
                content=content,
                related_objects=related_objects,
                tag=tag,
                template=template,
                state=self.get_initial_dialer_state(recipient),
                is_autodialer=is_autodialer,
                retry_sending=self.get_retry_sending(),
                **kwargs,
                **self._get_extra_message_kwargs()
            )
        except PersistenceException as ex:
            raise DialerSendingError(force_text(ex))
