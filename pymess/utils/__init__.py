from pymess.config import settings


def normalize_phone_number(number):
    """
    Function that normalize input phone number to the valid phone number format.
    """
    if number:
        number = number.replace(' ', '').replace('-', '')
        if len(number) == 9 and settings.SMS_DEFAULT_PHONE_CODE:
            number = ''.join((settings.SMS_DEFAULT_PHONE_CODE, number))
        elif len(number) == 14 and number.startswith('00'):
            number = '+' + number[2:]
    return number


def fullname(o):
    """
    Helper that returns name of the input object with its path.
    """
    return o.__module__ + "." + o.__class__.__name__
