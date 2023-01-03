from bs4 import BeautifulSoup

import requests

from enum import Enum

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from enumfields import IntegerChoicesEnum

from pymess.backend.sms import SMSBackend
from pymess.enums import OutputSMSMessageState
from pymess.utils.logged_requests import generate_session
from pymess.config import settings


class RequestType(str, Enum):

    SMS = 'SMS'
    DELIVERY_REQUEST = 'DELIVERY_REQUEST'


class SmsOperatorState(IntegerChoicesEnum):

    DELIVERED = 0,  _('delivered')
    NOT_DELIVERED = 1, _('not delivered')
    PHONE_NUMBER_NOT_EXISTS = 2, _('number not exists')

    # SMS not moved to GSM operator
    TIMEOUTED = 3, _('timeouted')
    INVALID_PHONE_NUMBER = 4, _('wrong number format')
    ANOTHER_ERROR = 5, _('another error')
    EVENT_ERROR = 6, _('event error')
    SMS_TEXT_TOO_LONG = 7, _('SMS text too long')

    # SMS with more parts
    PARTLY_DELIVERED = 10, _('partly delivered')
    UNKNOWN = 11, _('unknown')
    PARLY_DELIVERED_PARTLY_UNKNOWN = 12, _('partly delivered, partly unknown')
    PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN = 13, _('partly not delivered, partly unknown')
    PARTLY_DELIVERED_PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN = 14, ('partly delivered, partly not delivered, '
                                                                'partly unknown')
    NOT_FOUND = 15, _('not found')


class SMSOperatorBackend(SMSBackend):
    """
    SMS backend that implements ATS operator service https://www.sms-operator.cz/
    Backend supports check SMS delivery
    """

    class SMSOperatorSendingError(Exception):
        pass

    TEMPLATES = {
        'base': 'pymess/sms/sms_operator/base.xml',
        RequestType.SMS: 'pymess/sms/sms_operator/sms.xml',
        RequestType.DELIVERY_REQUEST: 'pymess/sms/sms_operator/delivery_request.xml',
    }

    SMS_OPERATOR_STATES_MAPPING = {
        SmsOperatorState.DELIVERED: OutputSMSMessageState.DELIVERED,
        SmsOperatorState.NOT_DELIVERED: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.PHONE_NUMBER_NOT_EXISTS: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.TIMEOUTED: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.INVALID_PHONE_NUMBER: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.ANOTHER_ERROR: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.EVENT_ERROR: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.SMS_TEXT_TOO_LONG: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.PARTLY_DELIVERED: OutputSMSMessageState.ERROR_UPDATE,
        SmsOperatorState.UNKNOWN: OutputSMSMessageState.SENDING,
        SmsOperatorState.PARLY_DELIVERED_PARTLY_UNKNOWN: OutputSMSMessageState.SENDING,
        SmsOperatorState.PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN: OutputSMSMessageState.SENDING,
        SmsOperatorState.PARTLY_DELIVERED_PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN: OutputSMSMessageState.SENDING,
        SmsOperatorState.NOT_FOUND: OutputSMSMessageState.ERROR_UPDATE,
    }

    config = {
        'URL': 'https://www.sms-operator.cz/webservices/webservice.aspx',
        'UNIQ_PREFIX': '',
        'TIMEOUT': 5,  # 5s
    }

    def _get_extra_sender_data(self):
        return {
            'prefix': self.config['UNIQ_PREFIX'],
        }

    def _serialize_messages(self, messages, request_type):
        """
        Serialize SMS messages to the XML
        :param messages: list of SMS messages
        :param request_type: type of the request to the SMS operator
        :return: serialized XML message that will be sent to the SMS operator service
        """
        return render_to_string(
            self.TEMPLATES['base'], {
                'username': self.config['USERNAME'],
                'password': self.config['PASSWORD'],
                'prefix': str(self.config['UNIQ_PREFIX']) + '-',
                'template_type': self.TEMPLATES[request_type],
                'messages': messages,
                'type': 'SMS' if request_type == RequestType.SMS else 'SMS-Status',
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
            resp = generate_session(slug='pymess - SMS operator', related_objects=list(messages)).post(
                self.config['URL'],
                data=requests_xml,
                headers={'Content-Type': 'text/xml'},
                timeout=self.config['TIMEOUT']
            )
            if resp.status_code != 200:
                raise self.SMSOperatorSendingError(
                    'SMS operator returned invalid response status code: {}'.format(resp.status_code)
                )
            self._update_sms_states_from_response(
                messages, self._parse_response_codes(resp.text), is_sending, **change_sms_kwargs
            )
        except requests.exceptions.RequestException as ex:
            raise self.SMSOperatorSendingError(
                'SMS operator returned returned exception: {}'.format(str(ex))
            )

    def _update_sms_states_from_response(self, messages, parsed_response, is_sending=False, **change_sms_kwargs):
        """
        Higher-level function performing serialization of SMS operator requests, parsing ATS server response and
        updating  SMS messages state according the received response.
        :param messages: list of SMS messages
        :param parsed_response: parsed HTTP response from the SMS operator service
        :param is_sending: True if update is called after sending message
        :param change_sms_kwargs: extra kwargs that will be stored to the message object
        """

        messages_dict = {message.pk: message for message in messages}

        missing_uniq = set(messages_dict.keys()) - set(parsed_response.keys())
        if missing_uniq:
            raise self.SMSOperatorSendingError(
                'SMS operator not returned SMS info with uniq: {}'.format(', '.join(map(str, missing_uniq)))
            )

        extra_uniq = set(parsed_response.keys()) - set(messages_dict.keys())
        if extra_uniq:
            raise self.SMSOperatorSendingError(
                'SMS operator returned SMS info about unknown uniq: {}'.format(', '.join(map(str, extra_uniq)))
            )

        for uniq, sms_operator_state in parsed_response.items():
            sms = messages_dict[uniq]
            state = self.SMS_OPERATOR_STATES_MAPPING.get(sms_operator_state)
            error = sms_operator_state.label if state == OutputSMSMessageState.ERROR_UPDATE else None
            if is_sending:
                if error:
                    self._update_message_after_sending_error(
                        sms,
                        state=state,
                        error=error,
                        extra_sender_data={'sender_state': sms_operator_state},
                        **change_sms_kwargs
                    )
                else:
                    self._update_message_after_sending(
                        sms,
                        state=state,
                        extra_sender_data={'sender_state': sms_operator_state},
                        **change_sms_kwargs
                    )
            else:
                self._update_message(
                    sms,
                    state=state,
                    error=error,
                    extra_sender_data={'sender_state': sms_operator_state},
                    **change_sms_kwargs
                )

    def publish_message(self, message):
        try:
            self._send_requests(
                [message],
                request_type=RequestType.SMS.value,
                is_sending=True,
                sent_at=timezone.now()
            )
        except self.SMSOperatorSendingError as ex:
            self._update_message_after_sending_error(
                message,
                state=OutputSMSMessageState.ERROR,
                error=str(ex)
            )
        except requests.exceptions.RequestException as ex:
            self._update_message_after_sending_error(
                message,
                error=str(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (lost of information
            # about exception).

    def publish_messages(self, messages):
        self._send_requests(messages, request_type=RequestType.SMS, is_sending=True, sent_at=timezone.now())

    def _parse_response_codes(self, xml):
        """
        Finds all <dataitem> tags in the given XML and returns a mapping "uniq" -> "response code" for all SMS.
        In case of an error, the error is logged.
        :param xml: XML from the SMS operator response
        :return: dictionary with pair {SMS uniq: response status code}
        """

        soup = BeautifulSoup(xml, 'html.parser')

        return {int(item.smsid.string.lstrip(self.config['UNIQ_PREFIX'] + '-')): SmsOperatorState(int(item.status.string))
                for item in soup.find_all('dataitem')}

    def update_sms_states(self, messages):
        self._send_requests(messages, request_type=RequestType.DELIVERY_REQUEST)
