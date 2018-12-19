from chamber.utils.datastructures import ChoicesEnum
from django.utils import timezone as tz
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _l

from pymess.backend.dialer import DialerBackend
from pymess.config import settings
from pymess.models import DialerMessage
from pymess.utils.logged_requests import generate_session


class DaktelaDialerBackend(DialerBackend):
    """
    Dialer backend implementing Daktela service https://www.daktela.com/api/v6/models/campaignsrecords
    """

    STATE = ChoicesEnum(
        ('NOT_ASSIGNED', _l('not assigned'), '0'),
        ('READY', _l('ready'), '1'),
        ('RESCHEDULED_BY_DIALER', _l('rescheduled by dialer'), '2'),
        ('CALL_IN_PROGRESS', _l('call in progress'), '3'),
        ('HANGUP', _l('hangup'), '4'),
        ('DONE', _l('done'), '5'),
        ('RESCHEDULED', _l('rescheduled'), '6'),
        ('ANSWERED_COMPLETE', _l('listened up complete message'), 'statuses_5c1394ec6ea23488631693'),
        ('ANSWERED_PARTIAL', _l('listened up partial message'), 'statuses_5c1394fa3ea76819966092'),
        ('UNREACHABLE', _l('unreachable'), 'statuses_5c13955d2a375138015786'),
        ('DECLINED', _l('declined'), 'statuses_5c13957c3cfcf286401391'),
        ('UNANSWERED', _l('unanswered'), 'statuses_5c13959a7e018235857206'),
    )

    STATES_MAPPING = {
        STATE.NOT_ASSIGNED: DialerMessage.STATE.NOT_ASSIGNED,
        STATE.READY: DialerMessage.STATE.READY,
        STATE.RESCHEDULED_BY_DIALER: DialerMessage.STATE.RESCHEDULED_BY_DIALER,
        STATE.CALL_IN_PROGRESS: DialerMessage.STATE.CALL_IN_PROGRESS,
        STATE.HANGUP: DialerMessage.STATE.HANGUP,
        STATE.DONE: DialerMessage.STATE.DONE,
        STATE.RESCHEDULED: DialerMessage.STATE.RESCHEDULED,
        STATE.ANSWERED_COMPLETE: DialerMessage.STATE.ANSWERED_COMPLETE,
        STATE.ANSWERED_PARTIAL: DialerMessage.STATE.ANSWERED_PARTIAL,
        STATE.UNREACHABLE: DialerMessage.STATE.UNREACHABLE,
        STATE.DECLINED: DialerMessage.STATE.DECLINED,
        STATE.UNANSWERED: DialerMessage.STATE.UNANSWERED,
    }

    SESSION_SLUG = 'pymess-daktela_autodialer'

    @staticmethod
    def _get_dialer_api_url(name=None):
        name = '/{name}'.format(name=name) if name else ''

        return '{base_url}{name}.json?accessToken={access_token}'.format(
            base_url=settings.DIALER_API_URL, name=name, access_token=settings.DIALER_API_ACCESS_TOKEN,
        )

    def _update_dialer_states(self, messages):
        """
        Method uses Daktela API to get info about autodialer call status
        :param messages: list of dialer messages to update
        """
        for message in messages:
            name = message.extra_data['name']
            client_url = self._get_dialer_api_url(name)
            response = generate_session(slug=self.SESSION_SLUG, related_objects=(message,)).get(client_url)
            resp_json = response.json()

            message.extra_data.update({
                'name': name,
                'daktela_action': resp_json['result']['action'],
                'daktela_statuses': resp_json['result']['statuses'],
            })
            resp_message_state = resp_json['result']['statuses'][0]['name'] if len(
                resp_json['result']['statuses']) else resp_json['result']['action']
            message_state = self.STATES_MAPPING[resp_message_state]
            message_error = resp_json['error'] if len(resp_json['error']) else None

            try:
                self.update_message(
                    message,
                    state=message_state,
                    error=message_error,
                    extra_data=message.extra_data,
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
                'queue': settings.DIALER_API_QUEUE,
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

            response = generate_session(slug=self.SESSION_SLUG, related_objects=(message,)).post(
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
