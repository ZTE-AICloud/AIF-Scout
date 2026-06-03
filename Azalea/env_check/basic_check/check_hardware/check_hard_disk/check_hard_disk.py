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
    from utils import tools
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
    from utils import tools

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_hard_disk.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)

SPLIT_DISK_MODEL = "[InspectorRet]Hard disk model:"
SPLIT_DISK_SIZE = "[InspectorRet]Hard disk total:"


def extract_data(raw_data):
    raw_data = raw_data.replace("[InspectorRet]", "")
    return raw_data


def parse_disk_model(line: str) -> str:
    model = ""
    ret = line.split(SPLIT_DISK_MODEL)
    if len(ret) >= 1:
        model = ret[1].strip()
    logger.info("hard disk model: %s", model)
    return model


def parse_disk_size(line: str) -> str:
    size = ""
    ret = line.split(SPLIT_DISK_SIZE)
    if len(ret) >= 1:
        size = ret[1].replace("GB", "").strip()
    logger.info("total hard disk: %s GB", size)
    return size


class CheckHardDiskTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="hard_disk_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check hard disk..."
            )
            logger.info("Start exec check hard disk...")

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
            logger.error(f"Check hard disk exception: {e}")

    def _handle_result(self, host_output, node_ids):
        hard_disk_model = self.task_options.task_params.get("hard_disk_model")
        hard_disk_size = str(
            self.task_options.task_params.get("hard_disk_size"))
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
            check_hard_disk_model = ""
            check_hard_disk_size = ""
            is_hard_disk_model_ok = False
            is_hard_disk_size_ok = False
            for line in stdout:
                detail_result.append(extract_data(line))
                if SPLIT_DISK_MODEL in line:
                    check_hard_disk_model = parse_disk_model(line)
                elif SPLIT_DISK_SIZE in line:
                    check_hard_disk_size = parse_disk_size(line)
            check_hard_disk_models = check_hard_disk_model.split(",")
            hard_disk_models = hard_disk_model.split(",")
            matched_models = tools.get_src_in_dst_list(
                check_hard_disk_models, hard_disk_models)
            if len(matched_models) == len(check_hard_disk_models):
                is_hard_disk_model_ok = True
            if check_hard_disk_size == hard_disk_size:
                is_hard_disk_size_ok = True
            format_result["data"].append(
                [
                    "Hard Disk Model",
                    check_hard_disk_model,
                    hard_disk_model,
                    (
                        TaskResult.NORMAL.value
                        if is_hard_disk_model_ok
                        else TaskResult.ABNORMAL.value
                    ),
                ]
            )
            format_result["data"].append(
                [
                    "Hard Disk Size(GB)",
                    check_hard_disk_size,
                    hard_disk_size,
                    (
                        TaskResult.NORMAL.value
                        if is_hard_disk_size_ok
                        else TaskResult.ABNORMAL.value
                    ),
                ]
            )
            status = (
                TaskStatus.SUCCESS.value
                if is_hard_disk_model_ok and is_hard_disk_size_ok
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.append(
                f"Hard disk model {'normal' if is_hard_disk_model_ok else 'abnormal'}"
            )
            detail_result.append(
                f"Hard disk size {'normal' if is_hard_disk_size_ok else 'abnormal'}"
            )
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
