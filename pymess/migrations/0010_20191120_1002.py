# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-11-20 10:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pymess', '0009_20191108_2007'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='emailmessage',
            name='require_pull_info',
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='info_changed_at',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='info changed at'),
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='last_webhook_received_at',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='last webhook received at'),
        ),
    ]
