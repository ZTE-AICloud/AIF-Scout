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
    from utils.consts import TaskStatus
    from utils.consts import TaskResult
except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus
    from utils.consts import TaskResult

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_gpu_state.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)


def extract_data(gpu_manufacturer, stdout):
    return_data = {}
    pattern = r'^(GPU\d+)-->memory used:([^,]+),process:(.+)$'
    for line in stdout:
        gpu_matches = re.search(pattern, line)
        if not gpu_matches:
            continue
        gpu_id, memory_used, process = gpu_matches.groups()
        if process != "None":
            process = "Not none"
        return_data[gpu_id] = {
            "memory_used": memory_used,
            "process": process
        }
    return return_data


class CheckGpuStateTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="gpu_state_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check gpu state..."
            )
            logger.info("Start exec check gpu state...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            host_ips = []
            host_config = []
            node_infos = {}
            gpu_manufacturers = []
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(user=node.username, port=node.port,
                               password=node.ssh_password)
                )
                node_infos[node.ip_address] = node
                gpu_manufacturers.append(node.gpu_manufacturer)

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
                host_args=gpu_manufacturers,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            self._handle_result(host_output, node_infos)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check gpu state exception: {e}")

    def _handle_result(self, host_output, node_infos):
        abnormal_host = []
        msg = ""

        for o in host_output:
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
            detail_result = []
            stdout = list(o.stdout)
            stderr = list(o.stderr)
            detail_result.extend(stdout)
            detail_result.extend(stderr)
            if o.exit_code != 0:
                abnormal_host.append(o.host)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} execute failed",
                    detail_result=detail_result,
                )
                continue
            format_result = []
            gpu_manufacturer = node_infos.get(o.host).gpu_manufacturer
            stdout_data = extract_data(gpu_manufacturer, stdout)
            gpu_count = node_infos.get(o.host).gpu_count
            gpu_smi_count = len(stdout_data)
            count_res_ok = (gpu_count == gpu_smi_count)
            format_count_result = {
                "result_type": "table",
                "title": "GPU lost check",
                "data": [
                    ["GPU Pcie count", "GPU smi count", "Result"],
                    [gpu_count, gpu_smi_count,
                        TaskResult.NORMAL.value if count_res_ok else TaskResult.ABNORMAL.value],
                ],
            }
            format_result.append(format_count_result)
            format_idle_result = {
                "result_type": "table",
                "title": "GPU idle check",
                "data": [
                    ["GPU", "Memory used", "Process", "Result"]
                ],
            }
            idle_res_ok = True
            for gpu_idx, state_info in stdout_data.items():
                res = TaskResult.NORMAL.value
                memory_used = state_info.get("memory_used", "")
                memory_used_num = memory_used.split()[0]
                process = state_info.get("process", "")
                if memory_used_num != "0" or process != "None":
                    res = TaskResult.ABNORMAL.value
                    idle_res_ok = False
                format_idle_result["data"].append(
                    [gpu_idx, memory_used, process, res])
            format_result.append(format_idle_result)
            status = TaskStatus.SUCCESS.value
            if not count_res_ok or not idle_res_ok:
                status = TaskStatus.FAILED.value
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
                detail_result,
                format_result,
                self.sync_check_node,
            )
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)
