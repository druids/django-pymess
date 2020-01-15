# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-12-19 10:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pymess', '0011_auto_20191210_1749'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialermessage',
            name='number_of_status_check_attempts',
            field=models.PositiveIntegerField(default=0, verbose_name='number of status check attempts'),
        ),
    ]