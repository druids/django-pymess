# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-27 15:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pymess', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailmessage',
            name='number_of_send_attempts',
            field=models.PositiveIntegerField(default=0, verbose_name='number of send attempts'),
        ),
    ]
