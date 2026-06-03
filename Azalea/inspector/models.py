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

import uuid

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import UniqueConstraint
from django.db.models import Lookup
from django.db.models import Field

from utils.consts import TASK_STATUS_CHOICES, FILE_TYPE_CHOICES, FILE_MANAGE_STATUS_CHOICES
from utils.consts import TaskStatus, FileManageStatus
from utils.decryption import EncryptedCharField


class TimestampMixin(models.Model):
    """时间戳混入类 - 消除重复代码"""
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def set_start_time(self):
        """设置开始时间"""
        if not self.start_time:
            self.start_time = timezone.now()

    def set_end_time(self):
        """设置结束时间"""
        self.end_time = timezone.now()


class NotEqual(Lookup):
    lookup_name = "ne"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s <> %s" % (lhs, rhs), params


Field.register_lookup(NotEqual)


class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None):
        if not username:
            raise ValueError("The Username field must be set")
        user = self.model(username=username)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        user = self.create_user(username, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username

    class Meta:
        app_label = "inspector"


class Node(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node_name = models.CharField(max_length=128, blank=True)
    username = models.CharField(max_length=128, null=False)
    ssh_password = EncryptedCharField(max_length=128, null=False)
    node_label = models.JSONField(default=dict, blank=True)
    gpu_manufacturer = models.CharField(max_length=128, blank=True, default="")
    gpu_type = models.CharField(max_length=128, blank=True, default="")
    gpu_count = models.IntegerField(default=0)
    is_primary_node = models.BooleanField(default=False)
    port = models.IntegerField(default=22)
    ip_address = models.GenericIPAddressField(blank=False, null=False)
    is_accessible = models.BooleanField(default=False)
    is_trusted = models.BooleanField(default=False)
    error_message = models.TextField(default="", blank=True)

    class Meta:
        app_label = "inspector"
        constraints = [UniqueConstraint(
            fields=["ip_address", "port"], name="unique_ip_port")]


class EnvCheckTask(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=128, default="")
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)
    nodes = models.JSONField(blank=True, default=list)  # List[str]
    msg = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        app_label = "inspector"


class EnvCheckNode(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        EnvCheckTask, on_delete=models.CASCADE, related_name="env_check_nodes")
    node_id = models.CharField(max_length=128, default="")
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)
    msg = models.TextField(blank=True, default="")

    class Meta:
        app_label = "inspector"


class EnvCheckItem(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        EnvCheckTask, on_delete=models.CASCADE, related_name="env_check_items")
    parent = models.CharField(max_length=128, default="")
    check_item = models.CharField(max_length=128, default="")
    param = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)
    msg = models.TextField(blank=True, default="")

    class Meta:
        app_label = "inspector"


class EnvCheckResult(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        EnvCheckTask, on_delete=models.CASCADE, related_name="env_check_results"
    )
    item = models.ForeignKey(
        EnvCheckItem, on_delete=models.CASCADE, related_name="env_check_results"
    )
    nodes = models.JSONField(blank=True, default=list)  # List[str]
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)
    msg = models.TextField(blank=True, default="")
    format_result = models.JSONField(blank=True, default=list)  # List[dict]
    detail_result = models.JSONField(blank=True, default=list)  # List[str]

    class Meta:
        app_label = "inspector"


class CustomFile(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES)
    file_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    file_size = models.PositiveIntegerField(blank=True, default=0)  # KB
    file_path = models.CharField(blank=True, max_length=255, default="")
    status = models.CharField(
        max_length=20, choices=FILE_MANAGE_STATUS_CHOICES, default=FileManageStatus.UPLOADING.value)
    additional_info = models.JSONField(blank=True, default=list)

    class Meta:
        app_label = "inspector"

    def __str__(self):
        return self.file_name


class ModelTask(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=128, default="")
    remote_data_path = models.CharField(max_length=255, default="")
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)

    class Meta:
        app_label = "inspector"


class NodeModelTask(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="node_model_tasks")
    task = models.ForeignKey(
        ModelTask, on_delete=models.CASCADE, related_name="node_model_tasks")
    task_type = models.CharField(max_length=128, default="")
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default=TaskStatus.ACCEPTED.value)
    progress = models.IntegerField(default=0)
    msg = models.TextField(blank=True, default="")
    finished_steps = models.JSONField(blank=True, default=list)
    estimated_end_time = models.DateTimeField(null=True, blank=True)
    target_result = models.JSONField(default=dict, blank=True)
    task_result = models.JSONField(default=dict, blank=True)
    task_info = models.JSONField(default=dict, blank=True)
    task_param = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "inspector"

    def set_start_time(self, estimated_time=0):
        if not self.start_time:
            self.start_time = timezone.now()
            if estimated_time != 0:
                self.estimated_end_time = self.start_time + timezone.timedelta(
                    minutes=estimated_time
                )
