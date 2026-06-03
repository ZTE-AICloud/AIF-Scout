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
SHELL_SCRIPT = "storage_nic_stress.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)

SPLIT_TITLE_RESULT = "[InspectorRet Title]"
SPLIT_ABNORMAL_RESULT = "[InspectorRet Abnormal]"
SPLIT_TABLE_RESULT = "[InspectorRet Table]"


def extract_data(raw_data):
    raw_data = raw_data.replace(SPLIT_TITLE_RESULT, "")
    raw_data = raw_data.replace(SPLIT_ABNORMAL_RESULT, "")
    raw_data = raw_data.replace(SPLIT_TABLE_RESULT, "")
    return raw_data


def parse_result_data(line: str, split_flag: str) -> List[str]:
    res = ""
    ret = line.split(split_flag)
    if len(ret) >= 1:
        res = ret[1].strip()
    return res.split(",")


class CheckStorNicStressTask(Task):
    PSSH_EXEC_TIMEOUT = 120

    metadata = TaskMetadata(
        check_item="storage_nic_stress",
    )

    def stop(self):
        logger.info("stop stor nic stress")
        self.stopped = True
        dest_path = DEST_PATH
        exec_cmd_on_multi_hosts_realtime(
            self.host_ips,
            self.host_config,
            f"chmod +x {dest_path} && {dest_path} 'stop' '' '' '' '' %s",
            host_args=self.arg_list,
            timeout=self.PSSH_EXEC_TIMEOUT,
            stop_on_errors=False,
        )

    @staticmethod
    def validate(request: dict):
        """validate task request.

        Args:
            request (dict): request data
        """

        nodes = request.get("nodes")
        if nodes is None or len(nodes) < 2:
            raise ValueError("Please select at least two nodes.")

    def execute(self) -> None:
        try:
            self.stopped = False
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check stor nic stress...")
            logger.info("Start exec check stor nic stress...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return
            if len(self.task_options.nodes) % 2 != 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "the count of selected nodes is not even")
                logger.error("the count of selected nodes is not even")
                return

            stor_nic = self.task_options.task_params.get("stor_nic")
            gid_index = self.task_options.task_params.get("gid_index")
            packet_size = self.task_options.task_params.get("packet_size")
            packet_count = self.task_options.task_params.get("packet_count")
            self.host_ips = []
            self.host_config = []
            node_ids = {}
            self.arg_list = []
            for node_a, node_b in zip(self.task_options.nodes[::2], self.task_options.nodes[1::2]):
                self.host_ips.append(node_a.ip_address)
                self.host_config.append(
                    HostConfig(user=node_a.username, port=node_a.port,
                               password=node_a.ssh_password)
                )
                node_ids[node_a.ip_address] = [node_a.node_id,
                                               node_a.ip_address, node_b.node_id, node_b.ip_address]
                self.arg_list.append(
                    f"{node_a.ip_address} {node_b.ip_address} {node_b.username} {node_b.ssh_password} {node_b.port}")

            # Distribute execution script
            local_path = LOCAL_PATH
            dest_path = DEST_PATH
            copy_file_to_multi_hosts(
                self.host_ips, self.host_config, local_path, dest_path, raise_error=False
            )
            if self.stopped:
                logger.info("stop stor nic stress success")
                return
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                self.host_ips,
                self.host_config,
                f"chmod +x {dest_path} && {dest_path} 'execute' '{stor_nic}' '{gid_index}' '{packet_size}' '{packet_count}' %s",
                host_args=self.arg_list,
                timeout=int(packet_count) * 1200,
                stop_on_errors=False,
            )
            if self.stopped:
                logger.info("stop stor nic stress success")
                return

            logger.debug(host_output)
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check stor nic stress exception: {e}")

    def _handle_result(self, host_output, node_ids):
        abnormal_host = []
        for o in host_output:
            node_a_id, node_a_ip, node_b_id, node_b_ip = node_ids.get(o.host)
            if o.exception:
                abnormal_host.extend([node_a_ip, node_b_ip])
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_a_id],
                    TaskStatus.FAILED.value,
                    f"{node_a_ip} raise an exception: {formatted_message}",
                )
                self.save_check_result_progress(
                    [node_b_id],
                    TaskStatus.FAILED.value,
                    f"{node_b_ip} raise an exception: {formatted_message}",
                )
                continue
            stdout = list(o.stdout)
            if o.exit_code != 0:
                abnormal_host.extend([node_a_ip, node_b_ip])
                self.save_check_result_progress(
                    [node_a_id],
                    TaskStatus.FAILED.value,
                    f"{node_a_ip} raise an exception",
                    detail_result=stdout,
                )
                self.save_check_result_progress(
                    [node_b_id],
                    TaskStatus.FAILED.value,
                    f"{node_b_ip} raise an exception",
                    detail_result=stdout,
                )
                continue
            result = TaskResult.NORMAL.value
            self.result_infos = {}
            self.result_infos[node_a_ip] = {
                "node_id": node_a_id,
                "format_results": [],
                "format_result": None,
                "detail_result": [],
                "result": TaskResult.NORMAL.value
            }
            self.result_infos[node_b_ip] = {
                "node_id": node_b_id,
                "format_results": [],
                "format_result": None,
                "detail_result": [],
                "result": TaskResult.NORMAL.value
            }
            for line in stdout:
                self.parse_result(line, node_a_ip, node_b_ip)

            for ip in [node_a_ip, node_b_ip]:
                if self.result_infos[ip]["format_result"] is not None:
                    self.result_infos[ip]["format_results"].append(
                        self.result_infos[ip]["format_result"])
                is_normal = (result == TaskResult.NORMAL.value)
                status = (
                    TaskStatus.SUCCESS.value
                    if is_normal else TaskStatus.FAILED.value
                )
                if status == TaskStatus.FAILED.value:
                    abnormal_host.append(ip)
                self.result_infos[ip]["detail_result"].append(
                    ip + " exec " + status)
                self.result_infos[ip]["detail_result"].extend(list(o.stderr))
                self.save_check_result_progress(
                    [self.result_infos[ip]["node_id"]],
                    status,
                    ip + " exec " + status,
                    self.result_infos[ip]["detail_result"],
                    self.result_infos[ip]["format_results"],
                )
        msg = ""
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)

    def parse_result(self, line, node_a_ip, node_b_ip):
        if f"{node_a_ip}:" in line:
            ips = [node_a_ip]
            line = line.replace(f"{node_a_ip}:", "")
        elif f"{node_b_ip}:" in line:
            ips = [node_b_ip]
            line = line.replace(f"{node_b_ip}:", "")
        else:
            ips = [node_a_ip, node_b_ip]
        if SPLIT_TITLE_RESULT in line:
            item = extract_data(line)
            for ip in ips:
                if self.result_infos[ip]["format_result"] is not None:
                    self.result_infos[ip]["format_results"].append(
                        self.result_infos[ip]["format_result"])
                    self.result_infos[ip]["format_result"] = None
                self.result_infos[ip]["format_results"].append({
                    "result_type": "string",
                    "title": item,
                })
        elif SPLIT_ABNORMAL_RESULT in line:
            item = extract_data(line)
            for ip in ips:
                if self.result_infos[ip]["format_result"] is not None:
                    self.result_infos[ip]["format_results"].append(
                        self.result_infos[ip]["format_result"])
                    self.result_infos[ip]["format_result"] = None
                self.result_infos[ip]["result"] = TaskResult.ABNORMAL.value
                self.result_infos[ip]["format_results"].append({
                    "result_type": "string",
                    "data": [item],
                })
                self.result_infos[ip]["detail_result"].append(item)
        elif SPLIT_TABLE_RESULT in line:
            item = parse_result_data(line, SPLIT_TABLE_RESULT)
            if len(item) == 0:
                return
            for ip in ips:
                if "abnormal" in item:
                    self.result_infos[ip]["result"] = TaskResult.ABNORMAL.value
                if self.result_infos[ip]["format_result"] is None:
                    self.result_infos[ip]["format_result"] = {
                        "result_type": "table",
                        "data": [item],
                    }
                else:
                    self.result_infos[ip]["format_result"]["data"].append(item)
        else:
            for ip in ips:
                self.result_infos[ip]["detail_result"].append(
                    extract_data(line))
