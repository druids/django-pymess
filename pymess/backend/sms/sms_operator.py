from bs4 import BeautifulSoup

import requests

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from chamber.utils.datastructures import ChoicesNumEnum, Enum

from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage
from pymess.utils.logged_requests import generate_session
from pymess.config import settings


class SMSOperatorBackend(SMSBackend):
    """
    SMS backend that implements ATS operator service https://www.sms-operator.cz/
    Backend supports check SMS delivery
    """

    class SMSOperatorSendingError(Exception):
        pass

    REQUEST_TYPES = Enum(
        'SMS',
        'DELIVERY_REQUEST',
    )

    TEMPLATES = {
        'base': 'pymess/sms/sms_operator/base.xml',
        REQUEST_TYPES.SMS: 'pymess/sms/sms_operator/sms.xml',
        REQUEST_TYPES.DELIVERY_REQUEST: 'pymess/sms/sms_operator/delivery_request.xml',
    }

    SMS_OPERATOR_STATES = ChoicesNumEnum(
        # SMS states
        ('DELIVERED', _('delivered'), 0),
        ('NOT_DELIVERED', _('not delivered'), 1),
        ('PHONE_NUMBER_NOT_EXISTS', _('number not exists'), 2),

        # SMS not moved to GSM operator
        ('TIMEOUTED', _('timeouted'), 3),
        ('INVALID_PHONE_NUMBER', _('wrong number format'), 4),
        ('ANOTHER_ERROR', _('another error'), 5),
        ('EVENT_ERROR', _('event error'), 6),
        ('SMS_TEXT_TOO_LONG', _('SMS text too long'), 7),

        # SMS with more parts
        ('PARTLY_DELIVERED', _('partly delivered'), 10),
        ('UNKNOWN', _('unknown'), 11),
        ('PARLY_DELIVERED_PARTLY_UNKNOWN', _('partly delivered, partly unknown'), 12),
        ('PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN', _('partly not delivered, partly unknown'), 13),
        ('PARTLY_DELIVERED_PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN',
         _('partly delivered, partly not delivered, partly unknown'), 14),
        ('NOT_FOUND', _('not found'), 15),
    )

    SMS_OPERATOR_STATES_MAPPING = {
        SMS_OPERATOR_STATES.DELIVERED: OutputSMSMessage.STATE.DELIVERED,
        SMS_OPERATOR_STATES.NOT_DELIVERED: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.PHONE_NUMBER_NOT_EXISTS: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.TIMEOUTED: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.INVALID_PHONE_NUMBER: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.ANOTHER_ERROR: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.EVENT_ERROR: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.SMS_TEXT_TOO_LONG: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.PARTLY_DELIVERED: OutputSMSMessage.STATE.ERROR_UPDATE,
        SMS_OPERATOR_STATES.UNKNOWN: OutputSMSMessage.STATE.SENDING,
        SMS_OPERATOR_STATES.PARLY_DELIVERED_PARTLY_UNKNOWN: OutputSMSMessage.STATE.SENDING,
        SMS_OPERATOR_STATES.PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN: OutputSMSMessage.STATE.SENDING,
        SMS_OPERATOR_STATES.PARTLY_DELIVERED_PARTLY_NOT_DELIVERED_PARTLY_UNKNOWN:
            OutputSMSMessage.STATE.SENDING,
        SMS_OPERATOR_STATES.NOT_FOUND: OutputSMSMessage.STATE.ERROR_UPDATE,
    }

    def __init__(self):
        self.config = settings.SMS_OPERATOR_CONFIG

    def _get_extra_sender_data(self):
        return {
            'prefix': self.config.UNIQ_PREFIX,
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
                'username': self.config.USERNAME,
                'password': self.config.PASSWORD,
                'prefix': str(self.config.UNIQ_PREFIX) + '-',
                'template_type': self.TEMPLATES[request_type],
                'messages': messages,
                'type': 'SMS' if request_type == self.REQUEST_TYPES.SMS else 'SMS-Status',
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
                self.config.URL,
                data=requests_xml,
                headers={'Content-Type': 'text/xml'},
                timeout=self.config.TIMEOUT
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
                'SMS operator returned returned exception: {}'.format(force_text(ex))
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
            error = (
                self.SMS_OPERATOR_STATES.get_label(sms_operator_state)
                if state == OutputSMSMessage.STATE.ERROR_UPDATE else None
            )
            if is_sending:
                self.update_message_after_sending(
                    sms,
                    state=state,
                    error=error,
                    extra_sender_data={'sender_state': sms_operator_state},
                    **change_sms_kwargs
                )
            else:
                self.update_message(
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
                request_type=self.REQUEST_TYPES.SMS,
                is_sending=True,
                sent_at=timezone.now()
            )
        except self.SMSOperatorSendingError as ex:
            self.update_message_after_sending(
                message,
                state=EmailMessage.STATE.ERROR_NOT_SENT,
                error=force_text(ex),
                retry_sending=False
            )
        except (requests.exceptions.RequestException, SMSOperatorSendingError) as ex:
            self.update_message_after_sending(
                message,
                state=EmailMessage.STATE.ERROR_NOT_SENT,
                error=force_text(ex)
            )
            # Do not re-raise caught exception. Re-raise exception causes transaction rollback (lost of information
            # about exception).

    def publish_messages(self, messages):
        self._send_requests(messages, request_type=self.REQUEST_TYPES.SMS, is_sending=True, sent_at=timezone.now())

    def _parse_response_codes(self, xml):
        """
        Finds all <dataitem> tags in the given XML and returns a mapping "uniq" -> "response code" for all SMS.
        In case of an error, the error is logged.
        :param xml: XML from the SMS operator response
        :return: dictionary with pair {SMS uniq: response status code}
        """

        soup = BeautifulSoup(xml, 'html.parser')

        return {int(item.smsid.string.lstrip(self.config.UNIQ_PREFIX + '-')): int(item.status.string)
                for item in soup.find_all('dataitem')}

    def _update_sms_states(self, messages):
        self._send_requests(messages, request_type=self.REQUEST_TYPES.DELIVERY_REQUEST)
