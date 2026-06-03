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
import json
from typing import List
from pssh.config import HostConfig
from pssh.output import HostOutput

from env_check.base import Task
from env_check.base import TaskMetadata
from utils.ssh_tool import copy_file_to_multi_hosts
from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
from utils.consts import TaskStatus
from utils.consts import TaskResult
from utils.consts import PathConfig

logger = logging.getLogger(__name__)
SHELL_SCRIPT = "check_gpu_pcie_link_state.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)

SPLIT_TABLE_RESULT = "[InspectorRet Table]"


def extract_data(raw_data):
    raw_data = raw_data.replace("[InspectorRet Table]", "")
    return raw_data


def parse_result_data(line: str, split_flag: str) -> List[str]:
    res = ""
    ret = line.split(split_flag)
    if len(ret) >= 1:
        res = ret[1].strip()
    return res.split(",")


class CheckGPUPCIeLinkStateTask(Task):
    PSSH_EXEC_TIMEOUT = 120
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="gpu_pcie_link_state_check",
    )

    def get_pcie_args(self, gpu_pci_info, gpu_manufacturer, gpu_type) -> str:
        gpu_infos = gpu_pci_info.get(gpu_manufacturer, [])
        for gpu_info in gpu_infos:
            if gpu_type in gpu_info.get("product_id", {}):
                verdor = gpu_info.get("vendor_id")
                product = gpu_info.get("product_id").get(gpu_type)
                return f"{verdor} {product}"
        return

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check gpu pcie link state...")
            logger.info("Start exec check gpu pcie link state...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            with open(PathConfig.GPU_PCI_JSON, "r") as f:
                gpu_pci_info = json.load(f)
            self.abnormal_host = []
            host_ips = []
            host_config = []
            host_args = []
            node_ids = {}
            for node in self.task_options.nodes:
                args = self.get_pcie_args(
                    gpu_pci_info, node.gpu_manufacturer, node.gpu_type)
                if args is None:
                    self.save_check_result_progress(
                        [node.node_id],
                        TaskStatus.FAILED.value,
                        node.ip_address + "can not find the pcie info of gpu",
                        [],
                        [],
                        self.sync_check_node,
                    )
                    self.abnormal_host.append(node.ip_address)
                    continue
                host_args.append(args)
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(user=node.username, port=node.port,
                               password=node.ssh_password)
                )
                node_ids[node.ip_address] = node.node_id
            logger.debug(f"node {node.node_id} args: {args}")
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
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check gpu pcie link state exception: {e}")

    def _handle_result(self, host_output, node_ids):
        for o in host_output:
            detail_result = []
            format_results = []
            node_id = node_ids.get(o.host)
            if o.exception:
                self.abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                    sync_check_node=self.sync_check_node,
                )
                continue
            stdout = list(o.stdout)
            if o.exit_code != 0:
                self.abnormal_host.append(o.host)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception",
                    detail_result=stdout,
                    sync_check_node=self.sync_check_node,
                )
                continue

            result = TaskResult.NORMAL.value
            format_result = None
            for line in stdout:
                if SPLIT_TABLE_RESULT in line:
                    item = parse_result_data(line, SPLIT_TABLE_RESULT)
                    if len(item) == 0:
                        continue
                    if "abnormal" in item:
                        result = TaskResult.ABNORMAL.value
                    if format_result is None:
                        format_result = {
                            "result_type": "table",
                            "data": [item],
                        }
                    else:
                        format_result["data"].append(item)
                else:
                    detail_result.append(extract_data(line))
            if format_result is not None:
                format_results.append(format_result)
            is_normal = (result == TaskResult.NORMAL.value)
            status = (
                TaskStatus.SUCCESS.value
                if is_normal else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                self.abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.extend(list(o.stderr))
            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
                detail_result,
                format_results,
                self.sync_check_node,
            )
        msg = ""
        if len(self.abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(self.abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)
