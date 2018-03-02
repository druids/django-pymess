from django.db import models

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


def has_int_pk(model):
    """
    Tests whether the given model has an integer primary key.
    """
    pk = model._meta.pk
    return (
        (
            isinstance(pk, (models.IntegerField, models.AutoField)) and
            not isinstance(pk, models.BigIntegerField)
        ) or (
            isinstance(pk, models.ForeignKey) and has_int_pk(pk.rel.to)
        )
    )


def fullname(o):
    """
    Helper that returns name of the input object with its path.
    """
    return o.__module__ + "." + o.__class__.__name__
