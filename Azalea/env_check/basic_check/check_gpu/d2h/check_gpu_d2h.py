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

import logging
import os
import re
from typing import List
from pssh.config import HostConfig
from pssh.output import HostOutput

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus, TaskResult, GpuManufacturer
except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus, TaskResult, GpuManufacturer

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_gpu_d2h.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)


def extract_data(gpu_manufacturer, stdout):
    """
    stdout:
        ["gpu 0 -> host: 25.08", "gpu 1 -> host: 25.0", ...]
    """
    return_data = {}
    for line in stdout:
        matches = re.search(r"gpu\s*(\d+)\s*->\s*host:\s*(\d+\.\d+)", line)
        if not matches:
            continue
        gpu_info = matches.groups()
        return_data.update({"gpu{}".format(gpu_info[0]): float(gpu_info[1])})
    return return_data


class CheckGpuDToHTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="gpu_d2h_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check gpu d2h..."
            )
            logger.info("Start exec check gpu d2h...")

            host_ips = []
            host_config = []
            host_args = []
            node_infos = {}
            image_host_ips = []
            image_host_config = []
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(user=node.username, port=node.port,
                               password=node.ssh_password)
                )
                host_args.append(f"-m '{node.gpu_manufacturer}'")
                node_infos[node.ip_address] = node

                if node.gpu_manufacturer == GpuManufacturer.NVIDIA.value:
                    image_host_ips.append(node.ip_address)
                    image_host_config.append(
                        HostConfig(user=node.username, port=node.port,
                                   password=node.ssh_password)
                    )

            logger.info("start copy test tool...")
            if len(image_host_ips) != 0:
                self.copy_env_check_image_file(
                    image_host_ips, image_host_config, node_infos)
            logger.info("finish copy test tool")

            # Distribute execution script
            local_path = LOCAL_PATH
            dest_path = DEST_PATH
            copy_file_to_multi_hosts(
                host_ips, host_config, local_path, dest_path, raise_error=False
            )
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_ips,
                host_config,
                f"chmod +x {dest_path} && {dest_path} %s",
                host_args=host_args,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            self._handle_result(host_output, node_infos)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check gpu d2h exception: {e}")

    def _handle_result(self, host_output, node_infos):
        threshold = float(
            self.task_options.task_params.get("bandwidth_threshold"))
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["GPU", "Actual", "Expected", "Result"]],
            }
            node_id = node_infos.get(o.host).node_id
            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                    sync_check_node=self.sync_check_node,
                )
                continue
            stdout = list(o.stdout)
            stderr = list(o.stderr)
            detail_result.extend(stdout)
            detail_result.extend(stderr)
            status = TaskStatus.FAILED.value
            if o.exit_code <= 0:
                status = TaskStatus.SUCCESS.value
            abnormal_results = []
            normal_results = []
            gpu_manufacturer = node_infos.get(o.host).gpu_manufacturer
            stdout_data = extract_data(gpu_manufacturer, stdout)
            for gpu_idx, bandwith in stdout_data.items():
                is_gpu_bw_ok = False
                if bandwith < threshold:
                    msg = (
                        o.host + " {} failed, actual bandwith {}, less than threshold:{}"
                    ).format(gpu_idx, bandwith, threshold)
                    abnormal_results.append(msg)
                else:
                    is_gpu_bw_ok = True
                    msg = (
                        o.host + " {} success, actual bandwith {}, larger than threshold:{}"
                    ).format(gpu_idx, bandwith, threshold)
                    normal_results.append(msg)
                format_result["data"].append(
                    [
                        gpu_idx,
                        bandwith,
                        threshold,
                        (TaskResult.NORMAL.value if is_gpu_bw_ok else TaskResult.ABNORMAL.value),
                    ]
                )
            status = (
                TaskStatus.SUCCESS.value
                if len(abnormal_results) == 0 and len(normal_results) > 0
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.extend(abnormal_results)
            detail_result.extend(normal_results)
            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
                detail_result,
                [format_result],
                self.sync_check_node,
            )
        msg = ""
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)
