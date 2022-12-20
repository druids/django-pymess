from bs4 import BeautifulSoup

import requests

from enum import Enum

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from enumfields import IntegerChoicesEnum

from pymess.backend.sms import SMSBackend
from pymess.enums import OutputSMSMessageState
from pymess.utils.logged_requests import generate_session


class RequestType(str, Enum):

    SMS = 'SMS'
    DELIVERY_REQUEST = 'DELIVERY_REQUEST'


class AtsState(IntegerChoicesEnum):

    # SMS delivery receipts
    NOT_FOUND = 20, _('not found')
    NOT_SENT = 21, _('not sent yet')
    SENT = 22, _('sent')
    DELIVERED = 23, _('delivered')
    NOT_DELIVERED = 24, _('not delivered')
    UNKNOWN = 25, _('not able to determine the state')
    # Authentication
    AUTHENTICATION_FAILED = 100, _('authentication failed')
    # Internal errors
    DB_ERROR = 200, _('DB error')
    # Request states
    OK = 0, _('SMS is OK and ready to be sent')
    UNSPECIFIED_ERROR = 1, _('unspecified error')
    BATCH_WITH_NOT_UNIQUE_UNIQ = 300, _('one of the requests has not unique "uniq"')
    SMS_NOT_UNIQUE_UNIQ = 310, _('SMS has not unique "uniq"')
    SMS_NO_KW = 320, _('SMS lacks keyword')
    KW_INVALID = 321, _('keyword not valid')
    NO_SENDER = 330, _('no sender specified')
    SENDER_INVALID = 331, _('sender not valid')
    MO_PR_NOT_ALLOWED = 332, _('MO PR SMS not allowed')
    MT_PR_NOT_ALLOWED = 333, _('MT PR SMS not allowed')
    MT_PR_DAILY_LIMIT = 334, _('MT PR SMS daily limit exceeded')
    MT_PR_TOTAL_LIMIT = 335, _('MT PR SMS total limit exceeded')
    GEOGRAPHIC_NOT_ALLOWED = 336, _('geographic number is not allowed')
    MT_SK_NOT_ALLOWED = 337, _('MT SMS to Slovakia not allowed')
    SHORTCODES_NOT_ALLOWED = 338, _('shortcodes not allowed')
    UNKNOWN_SENDER = 339, _('sender is unknown')
    UNSPECIFIED_SMS_TYPE = 340, _('type of SMS not specified')
    TOO_LONG = 341, _('SMS too long'),
    TOO_MANY_PARTS = 342, _('too many SMS parts (max. is 10)')
    WRONG_SENDER_OR_RECEIVER = 343, _('wrong number of sender/receiver')
    NO_RECIPIENT_OR_WRONG_FORMAT = 350, _('recipient is missing or in wrong format')
    TEXTID_NOT_ALLOWED = 360, _('using "textid" is not allowed')
    WRONG_TEXTID = 361, _('"textid" is in wrong format')
    LONG_SMS_TEXTID_NOT_ALLOWED = 362, _('long SMS with "textid" not allowed')
    # XML errors
    XML_MISSING = 701, _('XML body missing')
    XML_UNREADABLE = 702, _('XML is not readable')
    WRONG_HTTP_METHOD = 703, _('unknown HTTP method or not HTTP POST')
    XML_INVALID = 705, _('XML invalid')


class ATSSMSBackend(SMSBackend):
    """
    SMS backend that implements ATS operator service https://www.atspraha.cz/
    Backend supports check SMS delivery
    """

    TEMPLATES = {
        'base': 'pymess/sms/ats/base.xml',
        RequestType.SMS: 'pymess/sms/ats/sms.xml',
        RequestType.DELIVERY_REQUEST: 'pymess/sms/ats/delivery_request.xml',
    }

    class ATSSendingError(Exception):
        pass

    ATS_STATES_MAPPING = {
        AtsState.NOT_FOUND: OutputSMSMessageState.ERROR,
        AtsState.NOT_SENT: OutputSMSMessageState.SENDING,
        AtsState.SENT: OutputSMSMessageState.SENT,
        AtsState.DELIVERED: OutputSMSMessageState.DELIVERED,
        AtsState.NOT_DELIVERED: OutputSMSMessageState.ERROR,
        AtsState.OK: OutputSMSMessageState.SENDING,
        AtsState.UNSPECIFIED_ERROR: OutputSMSMessageState.ERROR,
        AtsState.BATCH_WITH_NOT_UNIQUE_UNIQ: OutputSMSMessageState.ERROR,
        AtsState.SMS_NOT_UNIQUE_UNIQ: OutputSMSMessageState.ERROR,
        AtsState.SMS_NO_KW: OutputSMSMessageState.ERROR,
        AtsState.KW_INVALID: OutputSMSMessageState.ERROR,
        AtsState.NO_SENDER: OutputSMSMessageState.ERROR,
        AtsState.SENDER_INVALID: OutputSMSMessageState.ERROR,
        AtsState.MO_PR_NOT_ALLOWED: OutputSMSMessageState.ERROR,
        AtsState.MT_SK_NOT_ALLOWED: OutputSMSMessageState.ERROR,
        AtsState.SHORTCODES_NOT_ALLOWED: OutputSMSMessageState.ERROR,
        AtsState.UNKNOWN_SENDER: OutputSMSMessageState.ERROR,
        AtsState.UNSPECIFIED_SMS_TYPE: OutputSMSMessageState.ERROR,
        AtsState.TOO_LONG: OutputSMSMessageState.ERROR,
        AtsState.TOO_MANY_PARTS: OutputSMSMessageState.ERROR,
        AtsState.WRONG_SENDER_OR_RECEIVER: OutputSMSMessageState.ERROR,
        AtsState.NO_RECIPIENT_OR_WRONG_FORMAT: OutputSMSMessageState.ERROR,
        AtsState.TEXTID_NOT_ALLOWED: OutputSMSMessageState.ERROR,
        AtsState.WRONG_TEXTID: OutputSMSMessageState.ERROR,
        AtsState.LONG_SMS_TEXTID_NOT_ALLOWED: OutputSMSMessageState.ERROR,
    }

    config = {
        'UNIQ_PREFIX': '',
        'VALIDITY': 60,
        'TEXTID': None,
        'URL': 'http://fik.atspraha.cz/gwfcgi/XMLServerWrapper.fcgi',
        'OPTID': '',
        'TIMEOUT': 5,  # 5s
    }

    def _get_extra_sender_data(self):
        return {
            'prefix': self.config['UNIQ_PREFIX'],
            'validity': self.config['VALIDITY'],
            'kw': self.config['PROJECT_KEYWORD'],
            'textid': self.config['TEXTID'],
        }

    def get_extra_message_kwargs(self):
        return {
            'sender': self.config['OUTPUT_SENDER_NUMBER'],
        }

    def _serialize_messages(self, messages, request_type):
        """
        Serialize SMS messages to the XML
        :param messages: list of SMS messages
        :param request_type: type of the request to the ATS operator
        :return: serialized XML message that will be sent to the ATS service
        """
        return render_to_string(
            self.TEMPLATES['base'], {
                'username': self.config['USERNAME'],
                'password': self.config['PASSWORD'],
                'template_type': self.TEMPLATES[request_type],
                'messages': messages,
                'prefix': str(self.config['UNIQ_PREFIX']) + '-',
                'sender': self.config['OUTPUT_SENDER_NUMBER'],
                'dlr': 1,
                'validity': self.config['VALIDITY'],
                'kw': self.config['PROJECT_KEYWORD'],
                'billing': 0,
                'extra': mark_safe(' textid="{textid}"'.format(
                    textid=self.config['TEXTID']
                )) if self.config['TEXTID'] else '',
            }
        )

    def _send_requests(self, messages, request_type, is_sending=False, **change_sms_kwargs):
        """
        Performs the actual POST request for input messages and request type.
        :param messages: list of SMS messages
        :param request_type: type of the request
        :param is_sending: True if method is called after sending message
        :param change_sms_kwargs: extra kwargs that will be stored to the message object
        """
        requests_xml = self._serialize_messages(messages, request_type)
        try:
            resp = generate_session(slug='pymess - ATS SMS', related_objects=list(messages)).post(
                self.config['URL'],
                data=requests_xml,
                headers={'Content-Type': 'text/xml'},
                timeout=self.config['TIMEOUT']
            )
            if resp.status_code != 200:
                raise self.ATSSendingError(
                    'ATS operator returned invalid response status code: {}'.format(resp.status_code)
                )
            self._update_sms_states_from_response(
                messages, self._parse_response_codes(resp.text), is_sending, **change_sms_kwargs
            )
        except requests.exceptions.RequestException as ex:
            raise self.ATSSendingError(
                'ATS operator returned returned exception: {}'.format(str(ex))
            )

    def _update_sms_states_from_response(self, messages, parsed_response, is_sending=False, **change_sms_kwargs):
        """
        Higher-level function performing serialization of ATS requests, parsing ATS server response and updating
        SMS messages state according the received response.
        :param messages: list of SMS messages
        :param parsed_response: parsed HTTP response from the ATS service
        :param is_sending: True if update is called after sending message
        :param change_sms_kwargs: extra kwargs that will be stored to the message object
        """

        messages_dict = {message.pk: message for message in messages}

        missing_uniq = set(messages_dict.keys()) - set(parsed_response.keys())
        if missing_uniq:
            raise self.ATSSendingError(
                'ATS operator not returned SMS info with uniq: {}'.format(', '.join(map(str, missing_uniq)))
            )

        extra_uniq = set(parsed_response.keys()) - set(messages_dict.keys())
        if extra_uniq:
            raise self.ATSSendingError(
                'ATS operator returned SMS info about unknown uniq: {}'.format(', '.join(map(str, extra_uniq)))
            )

        for uniq, ats_state in parsed_response.items():
            sms = messages_dict[uniq]
            state = self.ATS_STATES_MAPPING.get(ats_state)
            error = ats_state.label if state == OutputSMSMessageState.ERROR else None
            if is_sending:
                if error:
                    self._update_message_after_sending_error(
                        sms,
                        state=state,
                        error=error,
                        extra_sender_data={'sender_state': ats_state},
                        **change_sms_kwargs
                    )
                else:
                    self._update_message_after_sending(
                        sms,
                        state=state,
                        extra_sender_data={'sender_state': ats_state},
                        **change_sms_kwargs
                    )
            else:
                self._update_message(
                    sms,
                    state=state,
                    error=error,
                    extra_sender_data={'sender_state': ats_state},
                    **change_sms_kwargs
                )

    def publish_messages(self, messages):
        self._send_requests(messages, request_type=RequestType.SMS, is_sending=True, sent_at=timezone.now())

    def publish_message(self, message):
        try:
            self._send_requests(
                [message],
                request_type=RequestType.SMS,
                is_sending=True,
                sent_at=timezone.now()
            )
        except self.ATSSendingError as ex:
            self._update_message_after_sending_error(
                message,
                state=OutputSMSMessageState.ERROR,
                error=str(ex),
            )
        except requests.exceptions.RequestException as ex:
            # Service is probably unavailable sending will be retried
            self._update_message_after_sending_error(
                message,
                error=str(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (lost of information
            # about exception).

    def _parse_response_codes(self, xml):
        """
        Finds all <code> tags in the given XML and returns a mapping "uniq" -> "response code" for all SMS.
        In case of an error, the error is logged.
        :param xml: XML from the ATL response
        :return: dictionary with pair {SMS uniq: response status code}
        """

        soup = BeautifulSoup(xml, 'html.parser')
        code_tags = soup.find_all('code')

        error_messages = []
        for c in [int(error_code.string) for error_code in code_tags if not error_code.attrs.get('uniq')]:
            try:
                error_messages.append(AtsState(c).label)
            except ValueError:
                error_messages.append('ATS returned an unknown state {}.'.format(c))
        error_message = ', '.join(error_messages)

        if error_message:
            raise self.ATSSendingError('Error returned from ATS operator: {}'.format(error_message))

        return {
            int(code.attrs['uniq'].lstrip(str(self.config['UNIQ_PREFIX']) + '-')): AtsState(int(code.string))
            for code in code_tags if code.attrs.get('uniq')
        }

    def update_sms_states(self, messages):
        self._send_requests(messages, request_type=RequestType.DELIVERY_REQUEST)
