from pymess.config import settings


def normalize_phone_number(number):
    if number:
        number = number.replace(' ', '').replace('-', '')
        if len(number) == 9 and settings.SMS_DEFAULT_PHONE_CODE:
            number = ''.join((settings.SMS_DEFAULT_PHONE_CODE, number))
        elif len(number) == 14 and number.startswith('00'):
            number = '+' + number[2:]
    return number