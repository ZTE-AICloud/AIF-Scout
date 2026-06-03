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

from utils import tools, files
from typing import Dict
import shutil
import logging
from utils.consts import TASK_RUNNING_STATUS
from env_check.check_task import EnvCheckTask
import os
from collections import defaultdict
import datetime
from utils.consts import PathConfig
from inspector.serializers import EnvCheckTaskSerializer, EnvCheckItemResultSerializer, EnvCheckNodeResultSerializer
from rest_framework.exceptions import ValidationError
from inspector.repository import node_repository, env_check_repository

logger = logging.getLogger(__name__)


class EnvCheckService:

    def __init__(self):
        self.repository = env_check_repository.EnvCheckTaskRepository()
        self.item_repository = env_check_repository.EnvCheckItemRepository()
        self.result_repository = env_check_repository.EnvCheckResultRepository()

    def get_check_task(self, task_id: str):
        task = self.repository.find_by_id(task_id)
        return EnvCheckTaskSerializer(task, show_items=True).data

    def get_check_tasks(self, task_type: str):
        tasks = self.repository.find_all(task_type)
        return [EnvCheckTaskSerializer(task).data for task in tasks]

    def delete_check_tasks(self, task_data: Dict):
        task_ids = task_data.get("task_ids", [])
        if not task_ids:
            raise ValidationError("No task id for delete")
        tasks = self.repository.find_by_ids(task_ids)
        task_names = []
        failed_msgs = []
        for task in tasks:
            if task.status in TASK_RUNNING_STATUS:
                failed_msg = f"Check task {task.task_name} is {task.status}, not allowed to delete"
                failed_msgs.append(failed_msg)
                continue
            self.repository.delete(task)
            logger.info(f"{task.task_name} is deleted successfully")
            task_names.append(task.task_name)
        if failed_msgs:
            raise Exception(";".join(failed_msgs))

    def create_check_task(self, task_data: Dict):
        check_task = EnvCheckTask(task_data)
        check_task.create()
        return tools.change_model_item_to_str(check_task.env_check_task.id)

    def modify_check_task(self, task_id: str, task_data: Dict):
        check_task = EnvCheckTask(task_data, task_id)
        check_task.modify()

    def execute_check_task(self, task_id: str):
        check_task = EnvCheckTask(task_id=task_id)
        check_task.execute()

    def stop_check_task(self, task_id: str):
        check_task = EnvCheckTask(task_id=task_id)
        check_task.stop()

    def get_check_item_result(self, task_id: str, item_id: str):
        results = self.item_repository.find_by_item_id(item_id)
        return [EnvCheckItemResultSerializer(result).data for result in results]

    def get_check_node_result(self, task_id: str, node_id: str):
        task_items = self.item_repository.find_all(task_id)
        task_results = self.result_repository.find_all(task_id)
        node_results = [
            result for result in task_results if node_id in result.nodes]
        return [self._serialize_check_node_result(item, node_results) for item in task_items]

    def download_env_check_log(self, task_data: Dict):
        task_id = task_data.get("task_id")
        task_results = self.result_repository.find_all(task_id)
        grouped_results = defaultdict(list)
        for result in task_results:
            check_item_name = result.item.check_item
            grouped_results[check_item_name].append(result)
        grouped_results = dict(grouped_results)

        task = self.repository.find_by_id(task_id)
        nowtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        download_path = os.path.join(
            PathConfig.DOWNLOAD_DIR, f"{task.task_name}-{nowtime}")
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        result_path = os.path.join(os.path.dirname(
            download_path), f"{task.task_name}_{nowtime}.zip")

        self._gen_env_check_log(grouped_results, download_path, result_path)
        return result_path

    def _serialize_check_node_result(self, item, node_results):
        result = None
        for node_result in node_results:
            if node_result.item.check_item == item.check_item:
                result = node_result
                break
        item_info = {
            "parent": item.parent,
            "check_item": item.check_item,
            "param": item.param,
        }
        if not result:
            item_info.update(
                {
                    "status": item.status,
                    "msg": item.msg
                }
            )
            return item_info
        return EnvCheckNodeResultSerializer(result, item_info=item_info).data

    def _gen_env_check_log(self, grouped_results, download_path, result_path):
        repository = node_repository.NodeRepository()
        nodes = repository.find_all().values(
            "id", "node_name", "ip_address")
        node_infos = {str(node["id"]): node for node in nodes}
        for check_item, results in grouped_results.items():
            with open(f"{download_path}/{check_item}.log", "w", encoding="utf-8") as f:
                for result in results:
                    detail_str = "\n".join(
                        line for line in result.detail_result)
                    node_info = []
                    for node_id in result.nodes:
                        if node_id in node_infos:
                            node_name = node_infos[node_id]["node_name"]
                            ip_address = node_infos[node_id]["ip_address"]
                            node_info.append(f"{node_name}({ip_address})")
                        else:
                            node_info.append(node_id)
                    node_info = ",".join(node_info)
                    f.write(f"\n---------- result: {node_info} ----------\n")
                    f.write(detail_str + "\n")
        files.zip_files(download_path, result_path)
        shutil.rmtree(download_path)
