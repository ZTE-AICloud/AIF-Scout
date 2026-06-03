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

from inspector.services.model_task_service import ModelTaskService
from model_task.base import ModelTask, RUNNING_STATUS, EXECUTING_STATUS
from inspector.repository import model_task_repository

logger = logging.getLogger(__name__)


def restore_model_tasks():
    # 程序启动时处理停止中状态的任务
    model_repository = model_task_repository.ModelTaskRepository()
    node_model_repository = model_task_repository.NodeModelTaskRepository()

    stopping_tasks = model_repository.find_by_statuses(["stopping"])
    model_task_service = ModelTaskService()
    for task in stopping_tasks:
        try:
            logger.info(f"Set {task.task_name} stopping to stopped")
            task.status = "stopped"
            model_repository.save(task)
            node_tasks = node_model_repository.find_by_statuses(
                task.id, RUNNING_STATUS)
            for node_task in node_tasks:
                model_task_service.clean_node_task(node_task)
                node_task.status = "stopped"
                node_model_repository.save(node_task)
        except Exception as e:
            logger.error(
                f"Set {task.task_name} stopping to stopped failed: {str(e)}")

    # 程序启动时处理运行中状态的任务

    in_progress_tasks = model_repository.find_by_statuses(EXECUTING_STATUS)
    for task in in_progress_tasks:
        try:
            logger.info(f"{task.task_name} continue to run")
            task_info = {
                "task_id": task.id
            }
            model_task = ModelTask(task_info, action="restore")
            model_task.execute()
        except Exception as e:
            logger.error(f"{task.task_name} continue to run failed: {str(e)}")

    logger.info("restore model tasks finished.")
