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
SHELL_SCRIPT = "check_nic_state.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)


SPLIT_PARAM = "[InspectorRet Param]"
SPLIT_STOR = "[InspectorRet Stor]"


def extract_data(raw_data):
    raw_data = raw_data.replace(SPLIT_PARAM, "")
    raw_data = raw_data.replace(SPLIT_STOR, "")
    return raw_data


def parse_nic_state(line: str, split_flag: str):
    line = line.replace(split_flag, "")
    ret = line.split(":")
    if len(ret) < 2:
        return "", ""
    res = ret[1].split(",")
    speed = 0
    mtu = 0
    if len(res) >= 2 and res[1].isdigit():
        speed = int(res[1])
    if len(res) >= 3 and res[2].isdigit():
        mtu = int(res[2])
    return ret[0], res[0], speed, mtu


class CheckNicStateTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="nic_state_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check nic state...")
            logger.info("Start exec check nic state...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            param_nic = self.task_options.task_params.get("param_nic")
            stor_nic = self.task_options.task_params.get("stor_nic")
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
                f"chmod +x {dest_path} && {dest_path} {param_nic} {stor_nic}",
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check nic state exception: {e}")

    def _handle_result(self, host_output, node_ids):
        stor_nic = self.task_options.task_params.get("stor_nic")
        param_speed = self.task_options.task_params.get("param_nic_speed")
        stor_speed = self.task_options.task_params.get("stor_nic_speed")
        param_mtu = self.task_options.task_params.get("param_nic_mtu")
        stor_mtu = self.task_options.task_params.get("stor_nic_mtu")
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Nic name", "Type", "State", "Actual speed", "Expected speed", "Actual mtu", "Expected mtu", "Result"]],
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
            is_param_ok = True
            is_stor_ok = True
            for line in stdout:
                detail_result.append(extract_data(line))
                if SPLIT_PARAM in line:
                    nic_name, nic_state, nic_speed, nic_mtu = parse_nic_state(
                        line, SPLIT_PARAM)
                    result = TaskResult.NORMAL.value
                    if nic_state != "up" or (param_speed is not None and nic_speed != param_speed) or (param_mtu is not None and nic_mtu != param_mtu):
                        is_param_ok = False
                        result = TaskResult.ABNORMAL.value
                    format_result["data"].append(
                        [
                            nic_name,
                            "parameter nic",
                            nic_state,
                            f"{nic_speed} Mb/s",
                            f"{param_speed} Mb/s",
                            nic_mtu,
                            param_mtu,
                            result,
                        ]
                    )
                elif SPLIT_STOR in line:
                    nic_name, nic_state, nic_speed, nic_mtu = parse_nic_state(
                        line, SPLIT_STOR)
                    result = TaskResult.NORMAL.value
                    if nic_state != "up" or (stor_speed is not None and nic_speed != stor_speed) or (stor_mtu is not None and nic_mtu != stor_mtu):
                        is_stor_ok = False
                        result = TaskResult.ABNORMAL.value
                    format_result["data"].append(
                        [
                            nic_name,
                            "storage nic",
                            nic_state,
                            f"{nic_speed} Mb/s",
                            f"{stor_speed} Mb/s",
                            nic_mtu,
                            stor_mtu,
                            result,
                        ]
                    )
            status = (
                TaskStatus.SUCCESS.value
                if is_param_ok and is_stor_ok
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.append(
                f"parameter nic check {'normal' if is_param_ok else 'abnormal'}")
            if stor_nic is not None:
                detail_result.append(
                    f"storage nic check {'normal' if is_stor_ok else 'abnormal'}")
            detail_result.extend(list(o.stderr))
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
