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
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus
    from utils.consts import TaskResult

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_cpu.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)

SPLIT_CPU_MODEL = "[InspectorRet]CPU model name:"
SPLIT_CPU_COUNT = "[InspectorRet]CPU count:"


def extract_data(raw_data):
    raw_data = raw_data.replace("[InspectorRet]", "")
    return raw_data


def parse_cpu_model(line: str) -> str:
    model = ""
    ret = line.split(SPLIT_CPU_MODEL)
    if len(ret) >= 1:
        model = ret[1].strip()
    logger.info("cpu model: %s", model)
    return model


def parse_cpu_count(line: str) -> int:
    count = ""
    ret = line.split(SPLIT_CPU_COUNT)
    if len(ret) >= 1:
        count = ret[1].strip()
    logger.info("cpu count: %s", count)
    if count.isdigit():
        return int(count)
    return 0


class CheckCpuTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="cpu_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check cpu...")
            logger.info("Start exec check cpu...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            host_ips = []
            host_config = []
            node_ids = {}
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(user=node.username, port=node.port,
                               password=node.ssh_password)
                )
                node_ids[node.ip_address] = node.node_id

            # Distribute execution script
            local_path = LOCAL_PATH
            dest_path = DEST_PATH
            copy_file_to_multi_hosts(
                host_ips, host_config, local_path, dest_path, raise_error=False
            )
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_ips,
                host_config,
                f"chmod +x {dest_path} && {dest_path}",
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check cpu exception: {e}")

    def _handle_result(self, host_output, node_ids):
        cpu_model = self.task_options.task_params.get("cpu_model")
        cpu_count = self.task_options.task_params.get("cpu_count")
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Item", "Actual", "Expected", "Result"]],
            }
            node_id = node_ids.get(o.host)
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
            status = TaskStatus.FAILED.value
            if o.exit_code <= 0:
                status = TaskStatus.SUCCESS.value
            check_cpu_model = ""
            check_cpu_count = 0
            is_cpu_model_ok = False
            is_cpu_count_ok = False
            for line in stdout:
                detail_result.append(extract_data(line))
                if SPLIT_CPU_MODEL in line:
                    check_cpu_model = parse_cpu_model(line)
                elif SPLIT_CPU_COUNT in line:
                    check_cpu_count = parse_cpu_count(line)
            if check_cpu_model == cpu_model:
                is_cpu_model_ok = True
            if check_cpu_count == cpu_count:
                is_cpu_count_ok = True
            format_result["data"].append(
                [
                    "CPU Model",
                    check_cpu_model,
                    cpu_model,
                    (TaskResult.NORMAL.value if is_cpu_model_ok else TaskResult.ABNORMAL.value),
                ]
            )
            format_result["data"].append(
                [
                    "CPU Count",
                    check_cpu_count,
                    cpu_count,
                    (TaskResult.NORMAL.value if is_cpu_count_ok else TaskResult.ABNORMAL.value),
                ]
            )
            status = (
                TaskStatus.SUCCESS.value
                if is_cpu_model_ok and is_cpu_count_ok
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.append(
                f"CPU model {'normal' if is_cpu_model_ok else 'abnormal'}")
            detail_result.append(
                f"CPU count {'normal' if is_cpu_count_ok else 'abnormal'}")
            detail_result.extend(stderr)
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
