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

from utils.consts import TaskStatus, TASK_RUNNING_STATUS, TaskType
from inspector.repository import env_check_repository

logger = logging.getLogger(__name__)


def restore_env_check_tasks():
    task_repository = env_check_repository.EnvCheckTaskRepository()
    item_repository = env_check_repository.EnvCheckItemRepository()
    node_repository = env_check_repository.EnvCheckNodeRepository()

    running_tasks = task_repository.find_by_statuses(TASK_RUNNING_STATUS)

    for task in running_tasks:
        try:
            logger.info(
                f"Will restore env check task: {task.task_name} to stopped")

            task.status = TaskStatus.STOPPED.value
            task.msg = "The server was restarted! It has been restored to the stopped status."
            task.set_end_time()
            task_repository.save(task)

            for item in item_repository.find_by_statuses(task.id, TASK_RUNNING_STATUS):
                item.status = TaskStatus.STOPPED.value
                item.msg = "Item was restored to the stopped status."
                item.set_end_time()
                item_repository.save(item)

            if task.task_type == TaskType.BASIC.value:
                for node in node_repository.find_by_statuses(task.id, TASK_RUNNING_STATUS):
                    node.status = TaskStatus.STOPPED.value
                    node.msg = "Node was restored to the stopped status."
                    node.set_end_time()
                    node_repository.save(node)
        except Exception as e:
            logger.error(
                f"Restore env check task: {task.task_name} to stopped exception: {str(e)}")
