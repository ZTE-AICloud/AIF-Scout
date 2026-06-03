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

from env_check.base import Task
from env_check.base import TaskMetadata
from utils.ssh_tool import copy_file_to_multi_hosts
from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
from utils.consts import TaskStatus
from utils.consts import TaskResult

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_storage_bandwidth.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)

SPLIT_RESULT = "[InspectorRet]"


def extract_data(raw_data):
    raw_data = raw_data.replace("[InspectorRet]", "")
    return raw_data


def parse_result_data(line: str, split_flag: str):
    line = line.replace(split_flag, "")
    ret = line.split(",")
    if len(ret) < 3:
        return "", "", ""
    return ret[0], ret[1], ret[2]


class CheckStorageBandwidthTask(Task):
    PSSH_EXEC_TIMEOUT = 120

    metadata = TaskMetadata(
        check_item="storage_bandwidth_check",
    )

    def check_bandwidth_result(self, bandwidth: str, expected_bandwidth):
        try:
            ret = bandwidth.split()
            if len(ret) < 2:
                return TaskResult.ABNORMAL.value
            bandwidth_num = float(ret[0])
            if ret[1] == "GB/s":
                bandwidth_num = bandwidth_num * 1024
            elif ret[1] == "KB/s":
                bandwidth_num = bandwidth_num / 1024
            elif ret[1] == "TB/s":
                bandwidth_num = bandwidth_num * 1024 * 1024
            if bandwidth_num < expected_bandwidth:
                return TaskResult.ABNORMAL.value
            return TaskResult.NORMAL.value
        except Exception:
            return TaskResult.ABNORMAL.value

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check storage bandwidth...")
            logger.info("Start exec check storage bandwidth...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            shared_storage_path = self.task_options.task_params.get(
                "shared_storage_path")
            block_size = self.task_options.task_params.get("block_size")
            block_count = self.task_options.task_params.get("block_count")
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
                f"chmod +x {dest_path} && {dest_path} '{shared_storage_path}' '{block_size}' '{block_count}' %s",
                host_args=host_ips,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check storage bandwidth exception: {e}")

    def _handle_result(self, host_output, node_ids):
        expected_bandwidth = self.task_options.task_params.get("bandwidth")
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Data", "Time", "Bandwidth", "Expected bandwidth", "Result"]],
            }
            node_id = node_ids.get(o.host)
            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                )
                continue
            stdout = list(o.stdout)
            if o.exit_code != 0:
                abnormal_host.append(o.host)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception",
                    detail_result=stdout,
                )
                continue
            result = TaskResult.NORMAL.value
            for line in stdout:
                if SPLIT_RESULT in line:
                    data, time, bandwidth = parse_result_data(
                        line, SPLIT_RESULT)
                    result = self.check_bandwidth_result(
                        bandwidth, expected_bandwidth)
                    format_result["data"].append(
                        [
                            f"{data}",
                            f"{time}",
                            f"{bandwidth}",
                            f"{expected_bandwidth} MB/s",
                            result,
                        ]
                    )
                else:
                    detail_result.append(extract_data(line))
            is_normal = (result == TaskResult.NORMAL.value)
            status = (
                TaskStatus.SUCCESS.value
                if is_normal else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.extend(list(o.stderr))
            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
                detail_result,
                [format_result],
            )
        msg = ""
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)
