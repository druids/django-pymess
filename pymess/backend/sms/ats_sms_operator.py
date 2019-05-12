from bs4 import BeautifulSoup

import requests

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from chamber.utils.datastructures import ChoicesNumEnum, Enum

from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage
from pymess.utils.logged_requests import generate_session
from pymess.config import settings


class ATSSMSBackend(SMSBackend):
    """
    SMS backend that implements ATS operator service https://www.atspraha.cz/
    Backend supports check SMS delivery
    """

    REQUEST_TYPES = Enum(
        'SMS',
        'DELIVERY_REQUEST',
    )

    TEMPLATES = {
        'base': 'pymess/sms/ats/base.xml',
        REQUEST_TYPES.SMS: 'pymess/sms/ats/sms.xml',
        REQUEST_TYPES.DELIVERY_REQUEST: 'pymess/sms/ats/delivery_request.xml',
    }

    class ATSSendingError(Exception):
        pass

    ATS_STATES = ChoicesNumEnum(
        # SMS delivery receipts
        ('NOT_FOUND', _('not found'), 20),
        ('NOT_SENT', _('not sent yet'), 21),
        ('SENT', _('sent'), 22),
        ('DELIVERED', _('delivered'), 23),
        ('NOT_DELIVERED', _('not delivered'), 24),
        ('UNKNOWN', _('not able to determine the state'), 25),
        # Authentication
        ('AUTHENTICATION_FAILED', _('authentication failed'), 100),
        # Internal errors
        ('DB_ERROR', _('DB error'), 200),
        # Request states
        ('OK', _('SMS is OK and ready to be sent'), 0),
        ('UNSPECIFIED_ERROR', _('unspecified error'), 1),
        ('BATCH_WITH_NOT_UNIQUE_UNIQ', _('one of the requests has not unique "uniq"'), 300),
        ('SMS_NOT_UNIQUE_UNIQ', _('SMS has not unique "uniq"'), 310),
        ('SMS_NO_KW', _('SMS lacks keyword'), 320),
        ('KW_INVALID', _('keyword not valid'), 321),
        ('NO_SENDER', _('no sender specified'), 330),
        ('SENDER_INVALID', _('sender not valid'), 331),
        ('MO_PR_NOT_ALLOWED', _('MO PR SMS not allowed'), 332),
        ('MT_PR_NOT_ALLOWED', _('MT PR SMS not allowed'), 333),
        ('MT_PR_DAILY_LIMIT', _('MT PR SMS daily limit exceeded'), 334),
        ('MT_PR_TOTAL_LIMIT', _('MT PR SMS total limit exceeded'), 335),
        ('GEOGRAPHIC_NOT_ALLOWED', _('geographic number is not allowed'), 336),
        ('MT_SK_NOT_ALLOWED', _('MT SMS to Slovakia not allowed'), 337),
        ('SHORTCODES_NOT_ALLOWED', _('shortcodes not allowed'), 338),
        ('UNKNOWN_SENDER', _('sender is unknown'), 339),
        ('UNSPECIFIED_SMS_TYPE', _('type of SMS not specified'), 340),
        ('TOO_LONG', _('SMS too long'), 341),
        ('TOO_MANY_PARTS', _('too many SMS parts (max. is 10)'), 342),
        ('WRONG_SENDER_OR_RECEIVER', _('wrong number of sender/receiver'), 343),
        ('NO_RECIPIENT_OR_WRONG_FORMAT', _('recipient is missing or in wrong format'), 350),
        ('TEXTID_NOT_ALLOWED', _('using "textid" is not allowed'), 360),
        ('WRONG_TEXTID', _('"textid" is in wrong format'), 361),
        ('LONG_SMS_TEXTID_NOT_ALLOWED', _('long SMS with "textid" not allowed'), 362),
        # XML errors
        ('XML_MISSING', _('XML body missing'), 701),
        ('XML_UNREADABLE', _('XML is not readable'), 702),
        ('WRONG_HTTP_METHOD', _('unknown HTTP method or not HTTP POST'), 703),
        ('XML_INVALID', _('XML invalid'), 705),
    )

    ATS_STATES_MAPPING = {
        ATS_STATES.NOT_FOUND: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.NOT_SENT: OutputSMSMessage.STATE.SENDING,
        ATS_STATES.SENT: OutputSMSMessage.STATE.SENT,
        ATS_STATES.DELIVERED: OutputSMSMessage.STATE.DELIVERED,
        ATS_STATES.NOT_DELIVERED: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.OK: OutputSMSMessage.STATE.SENDING,
        ATS_STATES.UNSPECIFIED_ERROR: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.BATCH_WITH_NOT_UNIQUE_UNIQ: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.SMS_NOT_UNIQUE_UNIQ: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.SMS_NO_KW: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.KW_INVALID: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.NO_SENDER: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.SENDER_INVALID: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.MO_PR_NOT_ALLOWED: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.MT_SK_NOT_ALLOWED: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.SHORTCODES_NOT_ALLOWED: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.UNKNOWN_SENDER: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.UNSPECIFIED_SMS_TYPE: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.TOO_LONG: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.TOO_MANY_PARTS: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.WRONG_SENDER_OR_RECEIVER: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.NO_RECIPIENT_OR_WRONG_FORMAT: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.TEXTID_NOT_ALLOWED: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.WRONG_TEXTID: OutputSMSMessage.STATE.ERROR,
        ATS_STATES.LONG_SMS_TEXTID_NOT_ALLOWED: OutputSMSMessage.STATE.ERROR,
    }

    def __init__(self):
        self.config = settings.ATS_SMS_CONFIG

    def _get_extra_sender_data(self):
        return {
            'prefix': self.config.UNIQ_PREFIX,
            'validity': self.config.VALIDITY,
            'kw': self.config.PROJECT_KEYWORD,
            'textid': self.config.TEXTID,
        }

    def _get_extra_message_kwargs(self):
        return {
            'sender': self.config.OUTPUT_SENDER_NUMBER,
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
                'username': self.config.USERNAME,
                'password': self.config.PASSWORD,
                'template_type': self.TEMPLATES[request_type],
                'messages': messages,
                'prefix': str(self.config.UNIQ_PREFIX) + '-',
                'sender': self.config.OUTPUT_SENDER_NUMBER,
                'dlr': 1,
                'validity': self.config.VALIDITY,
                'kw': self.config.PROJECT_KEYWORD,
                'billing': 0,
                'extra': mark_safe(' textid="{textid}"'.format(
                    textid=self.config.TEXTID
                )) if self.config.TEXTID else '',
            }
        )

    def _send_requests(self, messages, request_type, **change_sms_kwargs):
        """
        Performs the actual POST request for input messages and request type.
        :param messages: list of SMS messages
        :param request_type: type of the request
        :param change_sms_kwargs: extra kwargs that will be stored to the message object
        """
        requests_xml = self._serialize_messages(messages, request_type)
        try:
            resp = generate_session(slug='pymess - ATS SMS', related_objects=list(messages)).post(
                self.config.URL,
                data=requests_xml,
                headers={'Content-Type': 'text/xml'},
                timeout=self.config.TIMEOUT
            )
            if resp.status_code != 200:
                raise self.ATSSendingError(
                    'ATS operator returned invalid response status code: {}'.format(resp.status_code)
                )
            self._update_sms_states_from_response(messages, self._parse_response_codes(resp.text), **change_sms_kwargs)
        except requests.exceptions.RequestException as ex:
            raise self.ATSSendingError(
                'ATS operator returned returned exception: {}'.format(force_text(ex))
            )

    def _update_sms_states_from_response(self, messages, parsed_response, **change_sms_kwargs):
        """
        Higher-level function performing serialization of ATS requests, parsing ATS server response and updating
        SMS messages state according the received response.
        :param messages: list of SMS messages
        :param parsed_response: parsed HTTP response from the ATS service
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
            error = self.ATS_STATES.get_label(ats_state) if state == OutputSMSMessage.STATE.ERROR else None
            self.update_message(
                sms,
                state=state,
                error=error,
                extra_sender_data={'sender_state': ats_state}
                **change_sms_kwargs
            )

    def publish_messages(self, messages):
        self._send_requests(messages, request_type=self.REQUEST_TYPES.SMS, sent_at=timezone.now())

    def publish_message(self, message):
        self._send_requests([message], request_type=self.REQUEST_TYPES.SMS, sent_at=timezone.now())

    def _parse_response_codes(self, xml):
        """
        Finds all <code> tags in the given XML and returns a mapping "uniq" -> "response code" for all SMS.
        In case of an error, the error is logged.
        :param xml: XML from the ATL response
        :return: dictionary with pair {SMS uniq: response status code}
        """

        soup = BeautifulSoup(xml, 'html.parser')
        code_tags = soup.find_all('code')

        error_message = ', '.join(
            [(force_text(self.ATS_STATES.get_label(c))
              if c in self.ATS_STATES.all
              else 'ATS returned an unknown state {}.'.format(c))
             for c in [int(error_code.string) for error_code in code_tags if not error_code.attrs.get('uniq')]],
        )

        if error_message:
            raise self.ATSSendingError('Error returned from ATS operator: {}'.format(error_message))

        return {
            int(code.attrs['uniq'].lstrip(str(self.config.UNIQ_PREFIX) + '-')): int(code.string)
            for code in code_tags if code.attrs.get('uniq')
        }

    def _update_sms_states(self, messages):
        self._send_requests(messages, request_type=self.REQUEST_TYPES.DELIVERY_REQUEST)
