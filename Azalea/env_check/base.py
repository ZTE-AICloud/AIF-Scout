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

from abc import ABC, abstractmethod
import threading
import re
import os
from typing import Dict, Optional
from typing import List
from typing import Any
from dataclasses import dataclass
from dataclasses import field
from pssh.output import HostOutput

from inspector import models
from utils import consts
from utils.consts import TaskStatus, TaskType, EnvCheckTool, GpuManufacturer
from utils import tools
from utils.ssh_tool import copy_file_to_multi_hosts, exec_cmd_on_multi_hosts_realtime
from utils.consts import PathConfig
from inspector.repository import env_check_repository

import logging

logger = logging.getLogger(__name__)

FINISHED_STATUS = consts.TASK_FINISHED_STATUS

THREAD_LOCK = threading.Lock()


@dataclass
class TaskMetadata:
    check_item: str


@dataclass
class NodeInfo:
    node_id: str
    node_name: str
    gpu_manufacturer: str
    gpu_type: str
    gpu_count: int
    username: str
    ip_address: str
    port: int
    ssh_password: str = None


@dataclass
class TaskOptions:
    timeout: int
    nodes: List[NodeInfo] = field(default_factory=list)
    task_params: Dict[str, Any] = field(default_factory=dict)


class Task(ABC):
    PSSH_EXEC_TIMEOUT = 60
    REMOTE_WORKSPACE = PathConfig.REMOTE_WORKSPACE
    TOOL_FILE_DIR = PathConfig.UPLOAD_TOOL_FILE_PATH

    def __init__(self):
        self.task_options: Optional(TaskOptions) = None
        self.env_check_item: Optional(models.EnvCheckItem) = None
        self.results: Dict[str, models.EnvCheckResult] = {}
        self.task_repository = env_check_repository.EnvCheckTaskRepository()
        self.node_repository = env_check_repository.EnvCheckNodeRepository()
        self.item_repository = env_check_repository.EnvCheckItemRepository()
        self.result_repository = env_check_repository.EnvCheckResultRepository()

    @property
    def name(self) -> str:
        self.__class__.__name__

    @property
    @abstractmethod
    def metadata(self) -> TaskMetadata:
        pass

    @staticmethod
    def validate(request: dict):
        """validate task request.

        Args:
            request (dict): request data
        """
        pass

    @abstractmethod
    def execute(self) -> None:
        pass

    def stop(self):
        pass

    def copy_image_combination(self, host_ips, host_config, node_infos):
        host_combination = {}
        if len(host_ips) != len(host_config):
            return host_combination

        for index, host_ip in enumerate(host_ips):
            node_info = node_infos.get(host_ip)
            if not node_info:
                continue
            if node_info.gpu_manufacturer == GpuManufacturer.NVIDIA.value:
                combination_key = "NVIDIA"
                image_file = EnvCheckTool.NVIDIA_IMAGE_NAME.value
                image_tag = EnvCheckTool.NVIDIA_IMAGE_TAG.value
                docker_params = EnvCheckTool.NVIDIA_DOCKER_PARAMS.value
            else:
                continue
            if combination_key in host_combination:
                host_combination[combination_key]["host_ips"].append(host_ip)
                host_combination[combination_key]["host_config"].append(
                    host_config[index])
            else:
                host_combination[combination_key] = {
                    "host_ips": [host_ip],
                    "host_config": [host_config[index]],
                    "image_file": image_file,
                    "image_tag": image_tag,
                    "docker_params": docker_params
                }
        return host_combination

    def copy_env_check_image_file(self, host_ips, host_config, node_infos) -> None:
        host_combination = self.copy_image_combination(
            host_ips, host_config, node_infos)
        if not host_combination:
            return

        for host_info in host_combination.values():
            source_file = os.path.join(
                self.TOOL_FILE_DIR, host_info['image_file'])
            if not os.path.exists(source_file):
                continue
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_info["host_ips"],
                host_info["host_config"],
                f"test -f {self.REMOTE_WORKSPACE}/{host_info['image_file']}",
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )
            host_ips_copy = []
            host_config_copy = []
            for output in host_output:
                if output.exception or output.exit_code == 0:
                    # 执行失败或者文件存在
                    continue
                try:
                    idx = host_info["host_ips"].index(output.host)
                    host_ips_copy.append(output.host)
                    host_config_copy.append(host_info["host_config"][idx])
                except ValueError:
                    continue
            if not host_ips_copy:
                continue

            copy_file_to_multi_hosts(
                host_ips_copy,
                host_config_copy,
                f"{self.TOOL_FILE_DIR}/{host_info['image_file']}",
                f"{self.REMOTE_WORKSPACE}/{host_info['image_file']}",
                raise_error=False
            )

    def run_container(self, host_ips, host_config, node_infos, ssh_port='2222'):
        host_combination = self.copy_image_combination(
            host_ips, host_config, node_infos)
        if not host_combination:
            return

        failed_hosts = []
        error_messages = []
        docker_name = EnvCheckTool.CHECK_CONTAINER_NAME.value

        for host_info in host_combination.values():
            cmd = f"""
            if ! docker inspect {docker_name} &>/dev/null; then
                docker load -i {self.REMOTE_WORKSPACE}{os.path.basename(host_info['image_file'])} && \
                docker run -d \\
                    --name {docker_name} \\
                    -e SSH_PORT={ssh_port} \\
                    -v $HOME/{self.REMOTE_WORKSPACE}:/azalea \\
                    --net host --privileged \\
                    {host_info['docker_params']} \\
                    {host_info['image_tag']}
            fi
            """
            logger.info(f"exec cmd: {cmd}")
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_info["host_ips"],
                host_info["host_config"],
                cmd,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )
            for output in host_output:
                if output.exception or output.exit_code != 0:
                    failed_hosts.append(output.host)
                    stderr = list(output.stderr)
                    error_msg = self.format_exception(
                        output.exception) if output.exception else f"{stderr}"
                    error_messages.append(
                        f"Host {output.host} failed: {error_msg}")

        return error_messages

    def _sync_executing_nodes_finished_status(self, env_check_task):
        if env_check_task.task_type != TaskType.BASIC.value:
            return
        if env_check_task.status not in FINISHED_STATUS:
            return
        for node in self.node_repository.find_by_statuses(env_check_task.id, consts.TASK_EXECUTING_STATUS):
            node.status = env_check_task.status
            if not node.msg:
                node.msg = f"The node checking is {node.status}"
            node.set_end_time()
            self.node_repository.save(node)

    def _update_check_task_by_item_progress(self):
        with THREAD_LOCK:
            env_check_task = self.env_check_item.task
            check_items = self.item_repository.find_all(env_check_task.id)
            finished_items = {
                item.id: item.status for item in check_items if item.status in FINISHED_STATUS
            }
            if len(finished_items) == len(check_items):
                if TaskStatus.FAILED.value in finished_items.values():
                    env_check_task.status = TaskStatus.FAILED.value
                elif env_check_task.status != TaskStatus.STOPPING.value:
                    env_check_task.status = TaskStatus.SUCCESS.value
                else:
                    env_check_task.status = TaskStatus.STOPPED.value
                logger.info(
                    f"Env check task {env_check_task.task_name} end, "
                    f"status: {env_check_task.status}"
                )
                if not env_check_task.msg:
                    env_check_task.msg = f"The task is {env_check_task.status}"
                env_check_task.set_end_time()
                self.task_repository.save(env_check_task)
                self._sync_executing_nodes_finished_status(env_check_task)

    def save_check_item_progress(self, status: str, msg: str = ""):
        if status != self.env_check_item.status:
            logger.info(
                f"{self.env_check_item.check_item} status: {self.env_check_item.status} -> {status}"
            )
        if msg and msg != self.env_check_item.msg:
            logger.info(f"{self.env_check_item.check_item} message: {msg}")
        self.env_check_item.status = status
        self.env_check_item.msg = msg

        if status in FINISHED_STATUS:
            self.env_check_item.set_end_time()
            if not self.env_check_item.msg:
                self.env_check_item.msg = f"The check item is {status}"
        self.item_repository.save(self.env_check_item)
        if status in FINISHED_STATUS:
            self._update_check_task_by_item_progress()

    def _update_check_node_progress(self, nodes: Optional[List]):
        if not nodes:
            return
        env_check_task = self.env_check_item.task

        check_nodes = self.node_repository.find_by_ids(
            env_check_task.id, nodes)
        items_count = self.item_repository.find_all(env_check_task.id).count()
        task_results = self.result_repository.find_all(env_check_task.id)
        for node in check_nodes:
            if node.status in FINISHED_STATUS:
                continue
            # contains lookup is not supported on this database backend(sqlite3).
            node_results = [
                result for result in task_results if node.node_id in result.nodes]
            if len(node_results) < items_count:
                continue
            finished_results = {
                result.id: result.status
                for result in node_results
                if result.status in FINISHED_STATUS
            }
            if len(finished_results) == len(node_results):
                if TaskStatus.FAILED.value in finished_results.values():
                    node.status = TaskStatus.FAILED.value
                elif node.status != TaskStatus.STOPPING.value:
                    node.status = TaskStatus.SUCCESS.value
                else:
                    node.status = TaskStatus.STOPPED.value
                logger.info(
                    f"Env check node {node.node_id} end, status: {node.status}")
                if not node.msg:
                    node.msg = f"The node checking is {node.status}"
                node.set_end_time()
                self.node_repository.save(node)

    def save_check_result_progress(
        self,
        nodes: Optional[List],
        status: str,
        msg: str = "",
        detail_result: Optional[List] = [],
        format_result: Optional[List] = [],
        sync_check_node: bool = False,
    ):
        if not nodes:
            return
        node_id = tools.list_to_unique_str(nodes)
        result = self.results.get(node_id, None)
        if not result:
            result = models.EnvCheckResult(
                item=self.env_check_item,
                task=self.env_check_item.task,
                nodes=nodes,
                status=status,
                msg=msg,
                detail_result=detail_result,
                format_result=format_result,
            )
            result.set_start_time()
            # save result instance
            self.result_repository.save(result)
            self.results[node_id] = result
            if sync_check_node:
                self._update_check_node_progress(nodes)
            return
        if status != result.status:
            logger.info(
                f"{self.env_check_item.check_item} on {node_id} result status: "
                f"{result.status} -> {status}"
            )
        if msg and msg != result.msg:
            logger.info(
                f"{self.env_check_item.check_item} on {node_id} result message: {msg}")
        result.status = status
        result.msg = msg
        if format_result:
            result.format_result = format_result
            logger.info(
                f"{self.env_check_item.check_item} on {node_id} format result: {format_result}"
            )
        if detail_result:
            if result.detail_result:
                result.detail_result.extend(detail_result)
            else:
                result.detail_result = detail_result
        if status in FINISHED_STATUS:
            result.set_end_time()
        self.result_repository.save(result)
        if sync_check_node:
            self._update_check_node_progress(nodes)

    def format_exception(self, e):
        """
        格式化异常信息。如果异常参数列表长度大于1，并且第一个参数是带有指定占位符（如 %s, %d 等）的字符串，
        则使用后续参数填充该字符串；否则，直接返回异常的字符串表示。

        :param e: 异常对象
        :return: 格式化后的异常信息字符串
        """
        placeholder_pattern = r"(%[sdioxXeEfFgG])"

        if (
            len(e.args) > 1
            and isinstance(e.args[0], str)
            and re.search(placeholder_pattern, e.args[0])
        ):
            try:
                formatted_message = e.args[0] % e.args[1:]
            except Exception:
                # 如果格式化失败（例如占位符和参数不匹配），则退回到str(e)
                formatted_message = str(e)
        else:
            formatted_message = str(e)

        return formatted_message
