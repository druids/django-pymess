# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-12-05 08:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

from pymess.config import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('pymess', '0002_emailmessage_number_of_send_attempts'),
    ]

    operations = [
        migrations.CreateModel(
            name='DialerMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('changed_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='changed at')),
                ('sent_at', models.DateTimeField(blank=True, editable=False, null=True, verbose_name='sent at')),
                ('recipient', models.CharField(max_length=20, verbose_name='recipient')),
                ('content', models.TextField(verbose_name='content')),
                ('template_slug',
                 models.SlugField(blank=True, editable=False, max_length=100, null=True, verbose_name='slug')),
                ('state', models.IntegerField(
                    choices=[(0, 'not assigned'), (1, 'ready'), (2, 'rescheduled by dialer'), (3, 'call in progress'),
                             (4, 'hangup'), (5, 'done'), (6, 'rescheduled'), (7, 'listened up complete message'),
                             (8, 'listened up partial message'), (9, 'unreachable'), (10, 'declined'),
                             (11, 'unanswered'), (66, 'error'), (77, 'debug'), ], editable=False,
                    verbose_name='state')),
                ('backend',
                 models.CharField(blank=True, editable=False, max_length=250, null=True, verbose_name='backend')),
                ('error', models.TextField(blank=True, editable=False, null=True, verbose_name='error')),
                ('extra_data',
                 models.TextField(blank=True, editable=False, null=True, verbose_name='extra data')),
                ('extra_sender_data',
                 models.TextField(blank=True, editable=False, null=True, verbose_name='extra sender data')),
                ('tag', models.SlugField(blank=True, editable=False, null=True, verbose_name='tag')),
            ],
            options={
                'verbose_name': 'dialer message',
                'verbose_name_plural': 'dialer messages',
                'ordering': ('-created_at',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DialerMessageRelatedObject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('changed_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='changed at')),
                ('object_id', models.TextField(verbose_name='ID of the related object')),
                ('object_id_int', models.PositiveIntegerField(blank=True, db_index=True, null=True,
                                                              verbose_name='ID of the related object in int format')),
                ('content_type',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType',
                                   verbose_name='content type of the related object')),
                ('dialer_message',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_objects',
                                   to='pymess.DialerMessage', verbose_name='dialer message')),
            ],
            options={
                'verbose_name': 'related object of a dialer message',
                'verbose_name_plural': 'related objects of dialer messages',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='DialerTemplate',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('changed_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='changed at')),
                ('slug', models.SlugField(editable=False, max_length=100, primary_key=True, serialize=False,
                                          verbose_name='slug')),
                ('body', models.TextField(null=True, verbose_name='message body')),
            ],
            options={
                'ordering': ('-created_at',),
                'verbose_name': 'dialer template',
                'verbose_name_plural': 'dialer templates',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='dialermessage',
            name='template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='dialer_messages', to=settings.DIALER_TEMPLATE_MODEL,
                                    verbose_name='template'),
        ),
    ]
