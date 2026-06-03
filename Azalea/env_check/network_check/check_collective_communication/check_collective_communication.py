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
import math
import os
from typing import List
from pssh.config import HostConfig
from pssh.output import HostOutput
from inspector.repository import node_repository

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus, TaskResult, GpuManufacturer, EnvCheckTool
except Exception:
    import sys
    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import copy_file_to_multi_hosts
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import TaskStatus, TaskResult, GpuManufacturer, EnvCheckTool

ALGBW_RESULT = "[Azalea]max algbw(GB/s):"
OUT_ALGBW_RESULT = "[Azalea]out max algbw(GB/s):"
IN_ALGBW_RESULT = "[Azalea]in max algbw(GB/s):"

logger = logging.getLogger(__name__)
NVIDIA_SHELL_SCRIPT = "check_nccl_test.sh"

CURRENT_DIR = os.path.dirname(__file__)
LOCAL_NVIDIA_PATH = os.path.join(CURRENT_DIR, "nvidia/")
DEST_PATH = Task.REMOTE_WORKSPACE

SUPPORTED_GPU_MANUFACTURERS = [GpuManufacturer.NVIDIA.value]


def extract_data(raw_data):
    raw_data = raw_data.replace("[Azalea]", "")
    return raw_data


def change_str_to_float(input: str) -> float:
    try:
        res = float(input)
        return res
    except Exception:
        return 0


def parse_algbw_result(line: str) -> float:
    algbw = ""
    ret = line.split(ALGBW_RESULT)
    if len(ret) >= 1:
        algbw = ret[1].strip()
    logger.info("algbw result: %s", algbw)
    return change_str_to_float(algbw)


def parse_out_algbw_result(line: str) -> float:
    algbw = ""
    ret = line.split(OUT_ALGBW_RESULT)
    if len(ret) >= 1:
        algbw = ret[1].strip()
    logger.info("out algbw result: %s", algbw)
    return change_str_to_float(algbw)


def parse_in_algbw_result(line: str) -> float:
    algbw = ""
    ret = line.split(IN_ALGBW_RESULT)
    if len(ret) >= 1:
        algbw = ret[1].strip()
    logger.info("in algbw result: %s", algbw)
    return change_str_to_float(algbw)


def split_array(arr, n):
    return [arr[i:i + n] for i in range(0, len(arr), n)]


class CheckCollCommTask(Task):
    PSSH_EXEC_TIMEOUT = 120

    metadata = TaskMetadata(
        check_item="collective_communication_test",
    )

    @staticmethod
    def validate(request: dict):
        nodes = request.get("nodes", [])
        items = request.get("items", [])
        for item in items:
            if item['check_item'] == "collective_communication_test":
                node_count = int(item['param']['node_count'])
                if len(nodes) % node_count != 0:
                    raise ValueError(
                        "the nodes selected is not a multiple of the param of nodes")

        # 不支持异构GPU类型
        repository = node_repository.NodeRepository()
        first_node = repository.find_by_id(nodes[0])
        reference_gpu_type = first_node.gpu_type
        for node_data in nodes:
            node = repository.find_by_id(node_data)
            if node.gpu_type != reference_gpu_type:
                raise ValueError(
                    "Mixed GPU types are not supported. All nodes must have the same GPU type.")
            if node.gpu_manufacturer not in SUPPORTED_GPU_MANUFACTURERS:
                raise ValueError(
                    f"GPU manufacturer {node.gpu_manufacturer} is not supported. Only {SUPPORTED_GPU_MANUFACTURERS} are supported.")

    def stop(self):
        logger.info("stop collective commuciation test")
        self.stopped = True
        self._cleanup_containers()

    def execute(self) -> None:
        try:
            self.stopped = False
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check collective commuciation...")
            logger.info("Start exec check collective commuciation...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            node_count = int(self.task_options.task_params.get("node_count"))
            bw_standard = self.task_options.task_params.get("bw_standard")
            gid_index = self.task_options.task_params.get("gid_index")
            gpu_count = self.task_options.task_params.get("gpu_count")
            tcp_nic = self.task_options.task_params.get("tcp_nic")
            algorithm = self.task_options.task_params.get("algorithm")
            begin_size = self.task_options.task_params.get("begin_size")
            end_size = self.task_options.task_params.get("end_size")
            step_factor = self.task_options.task_params.get("step_factor")
            iterations = self.task_options.task_params.get("iterations")
            warmup_iterations = self.task_options.task_params.get(
                "warmup_iterations")
            ssh_port = self.task_options.task_params.get("ssh_port")
            env_param = self.task_options.task_params.get("env_param")
            additional_param = self.task_options.task_params.get(
                "additional_param")

            check_params = f"'{algorithm}' '{begin_size}' '{end_size}' '{step_factor}' '{iterations}' '{warmup_iterations}'"
            exec_timeout = math.ceil(
                (iterations + warmup_iterations) / 10) + 600
            # 获取节点的IP和配置信息
            self.host_ips = []
            self.host_config = []
            host_config_map = {}
            node_infos = {}
            for node in self.task_options.nodes:
                config = HostConfig(user=node.username,
                                    port=node.port, password=node.ssh_password)
                self.host_ips.append(node.ip_address)
                self.host_config.append(config)
                host_config_map[node.ip_address] = config
                node_infos[node.ip_address] = node

            # 分发并启容器
            check_gpu_manufacturer = self.task_options.nodes[0].gpu_manufacturer
            if check_gpu_manufacturer in SUPPORTED_GPU_MANUFACTURERS:
                self.copy_env_check_image_file(
                    self.host_ips, self.host_config, node_infos)
                if self.stopped:
                    logger.info("stop collective commuciation test success")
                    return
                error_msg = self.run_container(
                    self.host_ips, self.host_config, node_infos, ssh_port)
                if error_msg:
                    self.save_check_item_progress(
                        TaskStatus.FAILED.value,
                        f"Failed to start containers: {error_msg}"
                    )
                    logger.error(f"Container startup failed: {error_msg}")
                    return
                else:
                    self.save_check_item_progress(
                        TaskStatus.INPROGRESS.value, "Container startup completed successfully")

            ip_info = {}
            abnormal_host = []
            # 检查每个tcp网卡的ip，NVIDIA单机也需要获取
            nic_ip_query_cmd = (
                "info=`ifconfig " + tcp_nic + " 2> /dev/null | grep -w inet`; "
                "[[ -n \"$info\" ]] && { echo \"$info\" | head -n 1 | awk '{print $2}'; } "
                "|| { ifconfig " + tcp_nic +
                " 2> /dev/null | grep -w inet6 | grep -Ev \"[[:space:]]fe80\" | "
                "head -n 1 | awk '{print $2}'; }"
            )

            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                self.host_ips,
                self.host_config,
                nic_ip_query_cmd,
                use_pty=True,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False
            )
            is_ip_info_ok = True
            for o in host_output:
                stdout = list(o.stdout)
                if len(stdout) == 0:
                    is_ip_info_ok = False
                    abnormal_host.append(o.host)
                else:
                    ip_info[o.host] = stdout[0]
            if not is_ip_info_ok:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value,
                    "get tcp nic ip info failed, {} not found nic info.".format(
                        ",".join(abnormal_host))
                )
                return

            # 将节点按node_count数分成多组，每组的0号节点作为主节点
            hosts_group = split_array(self.host_ips, node_count)
            logger.info(hosts_group)
            node_info_group = {
                hosts[0]: [node_infos[host] for host in hosts]
                for hosts in hosts_group
            }
            count = 1
            host_ips_new = []
            host_config_new = []
            arg_list = []
            trust_arg_list = []
            for host_group in hosts_group:
                logger.info("*********** {} *************".format(count))
                ips = []
                trust_arg = ""
                count = count + 1
                for i in range(len(host_group)):
                    host = host_group[i]
                    h_config = host_config_map[host]
                    ip = ip_info.get(host, "")
                    if i == 0:
                        host_ips_new.append(host)
                        host_config_new.append(h_config)
                    ips.append(ip)

                    if trust_arg:
                        trust_arg += " "
                    trust_arg += "{},{},{},{}".format(
                        ip, h_config.user, h_config.password, h_config.port
                    )
                arg_list.append("{} {}".format(",".join(ips), ssh_port))
                trust_arg_list.append(trust_arg)

            # 按GPU类型在容器内执行检查脚本
            self.docker_name = EnvCheckTool.CHECK_CONTAINER_NAME.value
            if check_gpu_manufacturer == GpuManufacturer.NVIDIA.value:
                local_path = LOCAL_NVIDIA_PATH
                dest_path = DEST_PATH
                copy_file_to_multi_hosts(
                    self.host_ips, self.host_config, local_path, dest_path, recurse=True)
                host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                    host_ips_new,
                    host_config_new,
                    f"docker exec {self.docker_name} bash /azalea/{NVIDIA_SHELL_SCRIPT} '{tcp_nic}' '{bw_standard}' '{gid_index}' '{gpu_count}' {check_params} '{env_param}' '{additional_param}' %s",
                    host_args=arg_list, use_pty=True, timeout=exec_timeout, stop_on_errors=False
                )

            else:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "Unsupported GPU type")
                return

            if self.stopped:
                logger.info("stop collective commuciation test success")
                return
            self._handle_result(host_output, node_info_group)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check exception: {e}")
        finally:
            self._cleanup_containers()

    def _handle_result(self, host_output, node_info_group):
        bw_standard = float(self.task_options.task_params.get("bw_standard"))
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Item", "Actual", "Expected", "Result"]],
            }
            node_infos = node_info_group.get(o.host)
            node_ids = [node_info.node_id for node_info in node_infos]
            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    node_ids,
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                )
                continue
            stdout = list(o.stdout)
            stderr = list(o.stderr)
            status = TaskStatus.FAILED.value
            is_algbw_ok = True
            has_algbw = False
            if o.exit_code == 0:
                status = TaskStatus.SUCCESS.value
            for line in stdout:
                detail_result.append(extract_data(line))
                if OUT_ALGBW_RESULT in line:
                    actual_algbw_result = parse_out_algbw_result(line)
                    result_type = "out algorithm bandwidth"
                elif IN_ALGBW_RESULT in line:
                    actual_algbw_result = parse_in_algbw_result(line)
                    result_type = "in algorithm bandwidth"
                elif ALGBW_RESULT in line:
                    actual_algbw_result = parse_algbw_result(line)
                    result_type = "algorithm bandwidth"
                else:
                    continue
                has_algbw = True
                if actual_algbw_result < bw_standard:
                    is_algbw_ok = False
                format_result["data"].append(
                    [
                        result_type,
                        actual_algbw_result,
                        bw_standard,
                        (TaskResult.NORMAL.value if actual_algbw_result >=
                         bw_standard else TaskResult.ABNORMAL.value),
                    ]
                )
            status = (
                TaskStatus.SUCCESS.value
                if has_algbw and is_algbw_ok
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.append(
                f"check collective commuciation {'normal' if is_algbw_ok else 'abnormal'}")
            detail_result.extend(stderr)
            self.save_check_result_progress(
                node_ids,
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

    def _cleanup_containers(self):
        """清理容器资源"""
        logger.info(f"Starting cleanup for container {self.docker_name}")

        cleanup_cmd = f"docker rm -f {self.docker_name}"
        host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
            self.host_ips,
            self.host_config,
            cleanup_cmd,
            use_pty=True,
            timeout=self.PSSH_EXEC_TIMEOUT,
            stop_on_errors=False
        )

        cleanup_failures = []
        for output in host_output:
            if output.exception or output.exit_code != 0:
                cleanup_failures.append(output.host)

        if cleanup_failures:
            error_msg = f"Container cleanup failed on hosts: {', '.join(cleanup_failures)}"
            logger.error(error_msg)
        else:
            logger.info(
                f"Successfully cleaned up container {self.docker_name} on all hosts")
