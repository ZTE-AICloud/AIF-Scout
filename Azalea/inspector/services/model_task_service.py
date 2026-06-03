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

import datetime
import logging
import os
import shutil
from typing import Dict

from model_task.base import ModelTask, RUNNING_STATUS, EXECUTING_STATUS
from utils import decryption, files, tools
from utils.ssh_tool import copy_file_from_single_node_to_local, exec_cmd_on_single_host
from utils.consts import PathConfig
from inspector.serializers import ModelTaskSerializer
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from inspector.repository.model_task_repository import ModelTaskRepository, NodeModelTaskRepository


logger = logging.getLogger(__name__)


PSSH_EXEC_TIMEOUT = 60
LOG_MAX_LINE = 1000


class ModelTaskService:

    def __init__(self):
        self.repository = ModelTaskRepository()
        self.node_repository = NodeModelTaskRepository()

    def get_model_task(self, task_id: str):
        task = self.repository.find_by_id(task_id)
        return ModelTaskSerializer(task).data

    def get_model_tasks(self):
        tasks = self.repository.find_all()
        return [ModelTaskSerializer(task).data for task in tasks]

    def delete_model_tasks(self, task_data: Dict):
        task_ids = task_data.get("task_ids", [])
        if not task_ids:
            raise ValidationError("No task id for delete")
        tasks = self.repository.find_by_ids(task_ids)
        task_names = []
        failed_msgs = []
        for task in tasks:
            if task.status in RUNNING_STATUS:
                failed_msg = f"Model task {task.task_name} is {task.status}, not allowed to delete"
                failed_msgs.append(failed_msg)
                continue
            for node_task in self.node_repository.find_all(task.id):
                self.clean_node_task(node_task)
            self.repository.delete(task)
            logger.info(f"{task.task_name} is deleted successfully")
            task_names.append(task.task_name)
        if failed_msgs:
            raise Exception(";".join(failed_msgs))

    def create_model_task(self, task_data: Dict):
        model_task = ModelTask(task_data, action="create")
        return tools.change_model_item_to_str(model_task.model_task.id)

    def execute_model_task(self, task_data: Dict):
        model_task = ModelTask(task_data, action="execute")
        model_task.execute()
        return tools.change_model_item_to_str(model_task.model_task.id)

    def stop_model_task(self, task_data: Dict):
        task_id = task_data.get("task_id")
        task = self.repository.find_by_id(task_id)
        if task.status not in EXECUTING_STATUS:
            raise Exception(
                f"Model task {task.task_name} is already {task.status}!")
        task.status = "stopping"
        self.repository.save(task)

    def download_result(self, task_data: Dict):
        task_id = task_data.get("task_id")
        node_ids = task_data.get("node_ids")
        if not task_id or not node_ids:
            raise ValidationError("No task id or node id for download")
        task = self.repository.find_by_id(task_id)
        download_dir = PathConfig.DOWNLOAD_DIR
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        download_path = os.path.join(download_dir, task.task_name)
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        for node_task in self.node_repository.find_all(task.id):
            if tools.change_model_item_to_str(node_task.node.id) in node_ids:
                self._download_node_result(node_task, download_path)

        nowtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        result_path = os.path.join(os.path.dirname(
            download_path), f"{task.task_name}_{nowtime}.zip")
        files.zip_files(download_path, result_path)
        shutil.rmtree(download_path)
        return result_path

    def view_result(self, task_data):
        # 验证请求参数
        task_id = task_data.get("task_id")
        node_id = task_data.get("node_id")
        if not task_id or not node_id:
            raise ValidationError("No task or node for view task result")

        # 获取任务对象
        task = self.repository.find_by_id(task_id)

        # 查找对应的节点任务
        node_task = next((nt for nt in self.node_repository.find_all(
            task.id) if tools.change_model_item_to_str(nt.node.id) == node_id), None)
        if not node_task:
            raise ObjectDoesNotExist("Cannot find node in task")

        node = node_task.node
        task_params = node_task.task_info.get("params", {})
        download_files = node_task.task_info.get("download_file", [])

        # 检查下载文件是否存在
        if not download_files:
            logger.error(f"No result file on {node.ip_address}")
            return ""

        log_file = download_files[0].format(**task_params)
        cmd = f"ls {log_file} && cat {log_file} | tail -n {LOG_MAX_LINE}"

        # 执行命令获取日志内容
        output = exec_cmd_on_single_host(
            node.username,
            node.ip_address,
            node.ssh_password,
            cmd,
            port=node.port,
            timeout=PSSH_EXEC_TIMEOUT,
        )

        if output.exit_code != 0 or not output.std_out:
            error_msg = f"Failed to get {task.task_name} result on {node.ip_address}"
            logger.error(error_msg)
            return ""
        return "\n".join(output.std_out)

    def _download_node_result(self, node_task, download_path):
        """下载节点结果文件"""
        task_params = node_task.task_info.get("params", {})
        download_files = node_task.task_info.get("download_file", [])
        if not download_files:
            return
        try:
            logger.info(
                f"Download {download_files} from {node_task.node.ip_address}")
            for file in download_files:
                file = file.format(**task_params)
                local_file = os.path.join(
                    download_path, os.path.basename(file))
                if os.path.exists(local_file):
                    continue
                copy_file_from_single_node_to_local(
                    node_task.node.username,
                    node_task.node.ip_address,
                    node_task.node.ssh_password,
                    file,
                    local_file,
                    port=node_task.node.port,
                )
        except Exception as e:
            logger.error(
                f"Download {download_files} from {node_task.node.ip_address} failed: {e}")
            raise Exception(
                f"Download {download_files} from {node_task.node.ip_address} failed: {e}")

    def clean_node_task(self, node_task):
        """
        Clean node tasks, including running tags and post clean commands.

        :param node_task: Object containing node information and task information
        """
        try:
            node = node_task.node
            logger.info(f"Starting to clean model task on {node.ip_address}.")

            def exec_and_log(cmd):
                output = exec_cmd_on_single_host(
                    node.username,
                    node.ip_address,
                    node.ssh_password,
                    cmd,
                    port=node.port,
                    timeout=PSSH_EXEC_TIMEOUT,
                )
                if output.exit_code != 0:
                    logger.error(
                        f"Clean cmd {cmd} on {node.ip_address} failed, error msg: {output.std_err}"
                    )
                else:
                    logger.info(
                        f"Clean cmd {cmd} on {node.ip_address} succeeded")
                return output

            task_params = node_task.task_info.get("params", {})
            post_cmd = node_task.task_info.get("post_cmd", [])
            for cmd in post_cmd:
                exec_and_log(cmd.format(**task_params))
        except Exception as e:
            logger.error(
                f"Cleaning task on {node_task.node.ip_address} failed: {e}")
