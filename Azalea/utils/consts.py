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

from enum import Enum
from pathlib import Path
from django.conf import settings


class PathConfig:
    BASE_DIR = Path(settings.BASE_DIR)
    MEDIA_DIR = Path(settings.MEDIA_ROOT)
    DOWNLOAD_DIR = BASE_DIR / "pv" / "download"

    UPLOAD_COMMON_FILE_PATH = MEDIA_DIR / "common_files"
    UPLOAD_TOOL_FILE_PATH = MEDIA_DIR / "tool_files"
    UPLOAD_MODEL_FILE_PATH = MEDIA_DIR / "model_files"

    # 远程路径
    REMOTE_WORKSPACE = "azalea/"
    PRIVATE_KEY_PATH = "~/.ssh/id_rsa"

    # 配置文件
    ETC_DIR = BASE_DIR / "etc"
    ETC_FILE = BASE_DIR / "azalea.conf"
    GPU_PCI_JSON = ETC_DIR / "gpu_pci.json"
    ENV_CHECK_CONFIG_JSON = ETC_DIR / "environment_check/environment_check_item.json"
    MODEL_TESTING_CONFIG_YML = ETC_DIR / "model_testing/model_testing_configure.yml"


class TaskStatus(Enum):
    """
    任务状态
    """

    ACCEPTED = "accepted"
    INPROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


TASK_STATUS_CHOICES = [
    ("accepted", "Accepted"),
    ("in_progress", "In Progress"),
    ("success", "Success"),
    ("failed", "Failed"),
    ("paused", "Paused"),
    ("stopping", "Stopping"),
    ("stopped", "Stopped"),
]

TASK_RUNNING_STATUS = [TaskStatus.INPROGRESS.value, TaskStatus.STOPPING.value]
TASK_EXECUTING_STATUS = [TaskStatus.INPROGRESS.value]
TASK_FINISHED_STATUS = [TaskStatus.FAILED.value,
                        TaskStatus.SUCCESS.value, TaskStatus.STOPPED.value]


class TaskType(Enum):
    """
    任务类型
    """

    BASIC = "basic"


class TaskResult(Enum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"


class GpuManufacturer(Enum):
    NVIDIA = "NVIDIA"


class DataType(Enum):
    BF16 = "BF16"
    FP16 = "FP16"
    FP32 = "FP32"
    TF32 = "TF32"
    INT8 = "INT8"


class EnvCheckTool(Enum):
    CPU_STRESS = "stress"
    MEMORY_STRESS = "stressapptest"
    DISK_STRESS = "fio"

    CHECK_CONTAINER_NAME = "azalea_env_check"
    NVIDIA_IMAGE_NAME = "azalea_nvidia_runtime_0.5.tar"
    NVIDIA_IMAGE_TAG = "azalea_nvidia_runtime:0.5"
    NVIDIA_DOCKER_PARAMS = "--gpus all"


class FileType(Enum):
    COMMON_FILE = "common_file"
    TOOL_FILE = "tool_file"
    MODEL_FILE = "model_file"


FILE_TYPE_CHOICES = [
    ("common_file", "Common File"),
    ("tool_file", "Tool File"),
    ("model_file", "Model File"),
]


class FileManageStatus(Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    DISTRIBUTING = "distributing"
    DISTRIBUTED = "distributed"
    DISTRIBUTE_FAILED = "distribute_failed"


FILE_MANAGE_STATUS_CHOICES = [
    ("uploading", "Uploading"),
    ("uploaded", "Uploaded"),
    ("distributing", "Distributing"),
    ("distributed", "Distributed"),
    ("distribute_failed", "DistributeFailed"),
]
