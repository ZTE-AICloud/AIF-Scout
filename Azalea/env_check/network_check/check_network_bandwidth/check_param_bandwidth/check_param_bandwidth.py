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
from pssh.config import HostConfig
from pssh.output import HostOutput
from typing import List

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus
    from utils.consts import TaskResult
    from utils.node_classify import classify_nodes_no_repeat
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
    from utils.node_classify import classify_nodes_no_repeat

logger = logging.getLogger(__name__)
SINGLE_SSH_EXEC_TIMEOUT = 10  # set timeout for each ssh exec
TIMES_FOR_2NODE_CHECK = 8  # 8 mlx devices per node. times = 8
TIMEOUT_COEFFICIENT = 18  # 2node check time

SHELL_SCRIPT_MANAGE_IP = "check_param_bandwidth_same_device.sh"
SHELL_SCRIPT_PARAM_IP = "check_param_bandwidth_same_device_paramip.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH_MANAGE_IP = os.path.join(CURRENT_DIR, SHELL_SCRIPT_MANAGE_IP)
DEST_PATH_MANAGE_IP = os.path.join(
    Task.REMOTE_WORKSPACE, SHELL_SCRIPT_MANAGE_IP)
LOCAL_PATH_PARAM_IP = os.path.join(CURRENT_DIR, SHELL_SCRIPT_PARAM_IP)
DEST_PATH_PARAM_IP = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT_PARAM_IP)


def extract_bandwidth_data(raw_data, target):
    bandwidths = {}
    parts = raw_data.split(": ")[1].split("  ")

    if len(parts) < 2:
        raise ValueError(f"The data format is incorrect: {parts}")

    bandwidths["bw_peak"] = float(
        parts[0].lstrip("bw_peak ").rstrip(" Gb/sec"))
    bandwidths["bw_average"] = float(
        parts[1].lstrip("bw_average ").rstrip(" Gb/sec"))
    bandwidths["check_status"] = bandwidths["bw_average"] >= target
    return bandwidths


class CheckParamBandwidthTask(Task):
    metadata = TaskMetadata(
        check_item="param_bandwidth_check",
    )

    @staticmethod
    def validate(request: dict):
        nodes = request.get("nodes", [])
        if len(nodes) < 2:
            raise ValueError(
                "The selected nodes must be greater than 1 ")

    def stop(self) -> None:
        logger.info("stop param network bandwidth check")
        try:
            host_ips, host_config = [], []
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(HostConfig(
                    user=node.username, port=node.port, password=node.ssh_password))

            algorithm = self.task_options.task_params.get(
                "algorithm", "ib_write_bw")

            if_param_ip_as_manage_channel = self.task_options.task_params.get(
                "if_param_ip_as_manage_channel", "false"
            ).lower()
            if_host_ip_as_manage_channel = if_param_ip_as_manage_channel not in [
                "true", "1"]
            dest_path = DEST_PATH_MANAGE_IP if if_host_ip_as_manage_channel else DEST_PATH_PARAM_IP
            script_name = os.path.basename(dest_path)

            stop_commands = [
                f"pkill -2 -f '{script_name}'",
                f"pkill -2 '{algorithm}'"
            ]

            logger.info(f"Stop commands to execute: {stop_commands}")

            for cmd in stop_commands:
                exec_cmd_on_multi_hosts_realtime(
                    host_ips,
                    host_config,
                    cmd,
                    stop_on_errors=False,
                    timeout=10
                )
                logger.info(f"Executed stop command success: {cmd}")

        except Exception as e:
            logger.error(f"Error in stop method: {e}")

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start Exec Check RDMA network bandwidth..."
            )
            logger.info("Start Exec Check RDMA network bandwidth...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected"
                )
                logger.error("no node selected")
                return

            logger.info(f"receive parameters {self.task_options.task_params}")

            # 入参
            network_devices = self.task_options.task_params.get(
                "param_nic", "")
            gid = self.task_options.task_params.get("gid_index")
            target_bandwidth = self.task_options.task_params.get(
                "target_bandwidth")
            if_param_ip_as_manage_channel = self.task_options.task_params.get(
                "if_param_ip_as_manage_channel"
            )
            ib_test_bw_args = self.task_options.task_params.get(
                "ib_test_bw_args", "")
            message_size = self.task_options.task_params.get(
                "message_size", 65536)
            queue_size = self.task_options.task_params.get(
                "queue_size", 1)
            algorithm = self.task_options.task_params.get(
                "algorithm", "ib_write_bw")

            network_devices = [
                network_device.strip() for network_device in network_devices.split(",")
            ]

            target_bandwidth = float(target_bandwidth)
            if if_param_ip_as_manage_channel in ["True", "true", "False", "false"]:
                if_param_ip_as_manage_channel = if_param_ip_as_manage_channel.lower()
                if_host_ip_as_manage_channel = (
                    False if if_param_ip_as_manage_channel == "true" else True
                )
            else:
                raise Exception(
                    "set param ip as RDMA check manage channel is not valid.")

            # 节点信息
            nodes = self.task_options.nodes
            host_ips, host_config, node_ids = [], [], {}

            for node in nodes:
                host_ips.append(node.ip_address)
                host_config.append(HostConfig(
                    user=node.username, port=node.port, password=node.ssh_password))
                node_ids[node.ip_address] = node.node_id

            # 跨机检测节点分组
            check_nodes_group = classify_nodes_no_repeat(nodes)
            # 添加节点内自检测组
            # check_nodes_group.append([(node, node) for node in nodes])

            # Distribute execution script
            local_path = (
                LOCAL_PATH_MANAGE_IP if if_host_ip_as_manage_channel else LOCAL_PATH_PARAM_IP
            )
            dest_path = DEST_PATH_MANAGE_IP if if_host_ip_as_manage_channel else DEST_PATH_PARAM_IP
            copy_file_to_multi_hosts(
                host_ips, host_config, local_path, dest_path, raise_error=False
            )

            network_devices_to_cmd = " ".join(network_devices)
            ssh_cmd = f"chmod +x {dest_path} && {dest_path} -t {SINGLE_SSH_EXEC_TIMEOUT} %s"

            node_pair_records = {}
            for nodes_sub_group in check_nodes_group:
                server_ips = []
                server_config = []
                host_args = []

                for node_pair in nodes_sub_group:
                    host1, port1, user1, passwd1 = (
                        node_pair[0].ip_address,
                        node_pair[0].port,
                        node_pair[0].username,
                        node_pair[0].ssh_password,
                    )
                    host2, port2, user2, passwd2 = (
                        node_pair[1].ip_address,
                        node_pair[1].port,
                        node_pair[1].username,
                        node_pair[1].ssh_password,
                    )
                    node_pair_records[host1] = (host1, host2)
                    server_ips.append(host1)
                    server_config.append(HostConfig(
                        user=user1, port=port1, password=passwd1))
                    host_args.append(
                        f"-h '{host1} {host2}' -p '{port1} {port2}' "
                        f"-u '{user1} {user2}' -P '{passwd1} {passwd2}' "
                        f"-d '{network_devices_to_cmd}' -g '{gid}' "
                        f"-a '{ib_test_bw_args}' -b '{algorithm}' "
                        f"-s '{message_size}' -q '{queue_size}'"
                    )

                pssh_exec_timeout = int(
                    TIMEOUT_COEFFICIENT * 1.5 + SINGLE_SSH_EXEC_TIMEOUT * TIMES_FOR_2NODE_CHECK
                )

                host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                    server_ips,
                    server_config,
                    ssh_cmd,
                    host_args=host_args,
                    timeout=pssh_exec_timeout,
                    stop_on_errors=False,
                )

                self._handle_result(host_output, node_ids,
                                    node_pair_records, target_bandwidth)

        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {str(e)}"
            )
            logger.error(f"Check RoCE network bandwidth exception: {e}")

    def _handle_result(self, host_output, node_ids, node_pair_records, target_bandwidth):
        roce_conf_error_message_all = []
        check_failed_message_all = []
        abnormal_host = []

        for o in host_output:
            node_pair = node_pair_records.get(o.host)
            node_id1 = node_ids.get(node_pair[0])
            node_id2 = node_ids.get(node_pair[1])
            node_id_pair = [node_id1, node_id2]
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Server", "Client", "Bandwidth", "Expected Bandwidth", "Result"]],
            }

            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    node_id_pair,
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                )
                continue

            stdout = list(o.stdout)
            stderr = list(o.stderr)
            logger.info(f"stdout: {stdout}, stderr: {stderr}")
            if o.exit_code != 0:
                abnormal_host.append(o.host)
                self.save_check_result_progress(
                    node_id_pair,
                    TaskStatus.FAILED.value,
                    f"{o.host} execute failed",
                    detail_result=stderr if stderr else stdout,
                )
                continue

            result = TaskResult.NORMAL.value

            for line in stdout:
                line = line.strip()
                if not line:
                    continue

                detail_result.append(line)

                # 解析服务器和客户端信息
                server_pattern = r"Server-([\d\.]+)-([\w]+)"
                client_pattern = r"Client-([\d\.]+)-([\w]+)"

                server_match = re.search(server_pattern, line)
                client_match = re.search(client_pattern, line)

                server_display = o.host
                client_display = node_pair[1]
                if server_match:
                    server_ip = server_match.group(1)
                    server_device = server_match.group(2)
                    server_display = f"{server_ip}({server_device})"

                if client_match:
                    client_ip = client_match.group(1)
                    client_device = client_match.group(2)
                    client_display = f"{client_ip}({client_device})"

                if "ERROR!" in line:
                    roce_conf_error_message_all.append(line)
                    result = TaskResult.ABNORMAL.value
                    # 记录错误到表格
                    format_result["data"].append([
                        server_display,
                        client_display,
                        "N/A",
                        f"{target_bandwidth} Gb/sec",
                        TaskResult.ABNORMAL.value
                    ])

                elif "FAILED!" in line:
                    check_failed_message_all.append(line)
                    result = TaskResult.ABNORMAL.value
                    # 记录失败到表格
                    format_result["data"].append([
                        server_display,
                        client_display,
                        "N/A",
                        f"{target_bandwidth} Gb/sec",
                        TaskResult.ABNORMAL.value
                    ])

                elif "SUCCESS!" in line:
                    try:
                        bandwidth_data = extract_bandwidth_data(
                            line, target_bandwidth)

                        if not bandwidth_data["check_status"]:
                            line = (
                                line.replace("SUCCESS!", "FAILED!") +
                                f" < {target_bandwidth} Gb/sec"
                            )
                            check_failed_message_all.append(line)
                            result = TaskResult.ABNORMAL.value

                            bandwidth_avg = bandwidth_data["bw_average"]
                            format_result["data"].append([
                                server_display,
                                client_display,
                                f"{bandwidth_avg} Gb/sec",
                                f"{target_bandwidth} Gb/sec",
                                TaskResult.ABNORMAL.value
                            ])
                        else:
                            bandwidth_avg = bandwidth_data["bw_average"]
                            format_result["data"].append([
                                server_display,
                                client_display,
                                f"{bandwidth_avg} Gb/sec",
                                f"{target_bandwidth} Gb/sec",
                                TaskResult.NORMAL.value
                            ])
                    except Exception as e:
                        result = TaskResult.ABNORMAL.value
                        detail_result.append(
                            f"Error parsing bandwidth data: {str(e)}")

            is_normal = (result == TaskResult.NORMAL.value)
            status = TaskStatus.SUCCESS.value if is_normal else TaskStatus.FAILED.value

            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)

            self.save_check_result_progress(
                node_id_pair,
                status,
                f"{o.host} exec {status}",
                detail_result,
                [format_result] if len(format_result["data"]) > 1 else [],
            )

        # 更新任务状态
        msg = ""
        if roce_conf_error_message_all or check_failed_message_all or abnormal_host:
            status = TaskStatus.FAILED.value
            error_details = []
            if roce_conf_error_message_all:
                error_details.extend(roce_conf_error_message_all)
            if check_failed_message_all:
                error_details.extend(check_failed_message_all)
            if abnormal_host:
                error_details.append(f"Abnormal hosts: {abnormal_host}")

            msg = "CHECK FAILED! " + "; ".join(error_details)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
            msg = "CHECK SUCCESS!"

        self.save_check_item_progress(status, msg)
