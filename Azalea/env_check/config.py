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

from typing import Dict, List

from env_check.base import Task, TaskMetadata

# basic check
from env_check.basic_check.check_hardware import (
    CheckCpuTask,
    CheckMemoryTask,
    CheckHardDiskTask,
    CheckRaidCardTask,
)
from env_check.basic_check.check_gpu import (
    CheckGpuInfoTask,
    CheckGpuDriverTask,
    CheckGpuStateTask,
    CheckGpuBF16Task,
    CheckGpuFP32Task,
    CheckGpuInt8Task,
    CheckGpuTF32Task,
    CheckGpuDToDTask,
    CheckGpuDToHTask,
    CheckGpuHToDTask,
    CheckGpuMemBWTask,
    CheckGpuTopoTask,
)
from env_check.basic_check.check_nic import (
    CheckNicStateTask,
    CheckNicDriverTask,
    CheckOpticalModuleHealthTask,
)
from env_check.basic_check.check_os_config import (
    CheckRoceNetworkConfigTask,
    CheckPCIeAcsTask,
    CheckCPUIdleStateTask,
)
from env_check.basic_check.check_pcie_link import (
    CheckNicPCIeLinkStateTask,
    CheckGPUPCIeLinkStateTask,
)

# network check
from env_check.network_check.nic_stress_test import (
    CheckRdmaBwLatPerfTask,
    CheckParamNicStressTask,
    CheckStorNicStressTask,
)
from env_check.network_check.check_collective_communication import CheckCollCommTask
from env_check.network_check.check_network_connection import (
    CheckPingNetworkConnectionTask,
    CheckROCENetworkConnectionTask
)
from env_check.network_check.check_network_bandwidth import (
    CheckStorageBandwidthTask,
    CheckParamBandwidthTask
)
from env_check.network_check.check_network_latency import (
    CheckRoCENetworkLatencyTask
)
CheckTasks: List[Task] = [
    # basic check
    CheckCpuTask,
    CheckMemoryTask,
    CheckHardDiskTask,
    CheckRaidCardTask,
    CheckGpuInfoTask,
    CheckGpuDriverTask,
    CheckGpuStateTask,
    CheckGpuBF16Task,
    CheckGpuFP32Task,
    CheckGpuInt8Task,
    CheckGpuTF32Task,
    CheckGpuDToDTask,
    CheckGpuDToHTask,
    CheckGpuHToDTask,
    CheckGpuMemBWTask,
    CheckGpuTopoTask,
    CheckNicStateTask,
    CheckNicDriverTask,
    CheckOpticalModuleHealthTask,
    CheckCPUIdleStateTask,
    CheckPCIeAcsTask,
    CheckRoceNetworkConfigTask,
    CheckNicPCIeLinkStateTask,
    CheckGPUPCIeLinkStateTask,
    # network check
    CheckRdmaBwLatPerfTask,
    # collective_communication check
    CheckCollCommTask,
    CheckPingNetworkConnectionTask,
    CheckROCENetworkConnectionTask,
    CheckStorageBandwidthTask,
    CheckParamBandwidthTask,
    CheckRoCENetworkLatencyTask,
    CheckParamNicStressTask,
    CheckStorNicStressTask,
]

_task_cls_mapping: Dict[str, Task] = {}
for task_cls in CheckTasks:
    meta: TaskMetadata = task_cls.metadata
    _task_cls_mapping[meta.check_item] = task_cls


get_task_by_check_item = lambda check_item: _task_cls_mapping.get(check_item)  # noqa
