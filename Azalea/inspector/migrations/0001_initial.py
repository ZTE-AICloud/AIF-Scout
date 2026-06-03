# Copyright 2025 ZTE Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import django.db.models.deletion
import utils.decryption
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomFile',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('file_type', models.CharField(choices=[('common_file', 'Common File'), (
                    'tool_file', 'Tool File'), ('model_file', 'Model File')], max_length=50)),
                ('file_name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('file_size', models.PositiveIntegerField(blank=True, default=0)),
                ('file_path', models.CharField(
                    blank=True, default='', max_length=255)),
                ('status', models.CharField(choices=[('uploading', 'Uploading'), ('uploaded', 'Uploaded'), ('distributing', 'Distributing'), (
                    'distributed', 'Distributed'), ('distribute_failed', 'DistributeFailed')], default='uploading', max_length=20)),
                ('additional_info', models.JSONField(blank=True, default=list)),
            ],
        ),
        migrations.CreateModel(
            name='EnvCheckItem',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('parent', models.CharField(default='', max_length=128)),
                ('check_item', models.CharField(default='', max_length=128)),
                ('param', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
                ('msg', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='EnvCheckTask',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('task_name', models.CharField(max_length=255, unique=True)),
                ('task_type', models.CharField(default='', max_length=128)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
                ('nodes', models.JSONField(blank=True, default=list)),
                ('msg', models.TextField(blank=True, default='')),
                ('description', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='ModelTask',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('task_name', models.CharField(max_length=255, unique=True)),
                ('task_type', models.CharField(default='', max_length=128)),
                ('remote_data_path', models.CharField(default='', max_length=255)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(
                    max_length=128, verbose_name='password')),
                ('is_superuser', models.BooleanField(default=False,
                 help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(max_length=150, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('last_login', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                 related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.',
                 related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
        ),
        migrations.CreateModel(
            name='EnvCheckResult',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('nodes', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
                ('msg', models.TextField(blank=True, default='')),
                ('format_result', models.JSONField(blank=True, default=list)),
                ('detail_result', models.JSONField(blank=True, default=list)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='env_check_results', to='inspector.envcheckitem')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='env_check_results', to='inspector.envchecktask')),
            ],
        ),
        migrations.CreateModel(
            name='EnvCheckNode',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('node_id', models.CharField(default='', max_length=128)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
                ('msg', models.TextField(blank=True, default='')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='env_check_nodes', to='inspector.envchecktask')),
            ],
        ),
        migrations.AddField(
            model_name='envcheckitem',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='env_check_items', to='inspector.envchecktask'),
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('node_name', models.CharField(blank=True, max_length=128)),
                ('username', models.CharField(max_length=128)),
                ('ssh_password', utils.decryption.EncryptedCharField(max_length=128)),
                ('node_label', models.JSONField(blank=True, default=dict)),
                ('gpu_manufacturer', models.CharField(
                    blank=True, default='', max_length=128)),
                ('gpu_type', models.CharField(
                    blank=True, default='', max_length=128)),
                ('gpu_count', models.IntegerField(default=0)),
                ('is_primary_node', models.BooleanField(default=False)),
                ('port', models.IntegerField(default=22)),
                ('ip_address', models.GenericIPAddressField()),
                ('is_accessible', models.BooleanField(default=False)),
                ('is_trusted', models.BooleanField(default=False)),
                ('error_message', models.TextField(blank=True, default='')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('ip_address', 'port'), name='unique_ip_port')],
            },
        ),
        migrations.CreateModel(
            name='NodeModelTask',
            fields=[
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True, serialize=False)),
                ('task_type', models.CharField(default='', max_length=128)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('success', 'Success'), (
                    'failed', 'Failed'), ('paused', 'Paused'), ('stopping', 'Stopping'), ('stopped', 'Stopped')], default='accepted', max_length=20)),
                ('progress', models.IntegerField(default=0)),
                ('msg', models.TextField(blank=True, default='')),
                ('finished_steps', models.JSONField(blank=True, default=list)),
                ('estimated_end_time', models.DateTimeField(blank=True, null=True)),
                ('target_result', models.JSONField(blank=True, default=dict)),
                ('task_result', models.JSONField(blank=True, default=dict)),
                ('task_info', models.JSONField(blank=True, default=dict)),
                ('task_param', models.JSONField(blank=True, default=dict)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='node_model_tasks', to='inspector.node')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='node_model_tasks', to='inspector.modeltask')),
            ],
        ),
    ]
