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
import threading
from typing import Dict, Optional

from django.db.models import Case, When

from inspector import models
from utils.consts import TaskType, TaskStatus
from utils.consts import TASK_RUNNING_STATUS, TASK_EXECUTING_STATUS
from utils import decryption
from utils import tools
from utils import files
from utils.task_executor import validate_task_name
from env_check.config import get_task_by_check_item
from env_check.base import NodeInfo, TaskOptions, Task
from inspector.repository import node_repository, env_check_repository

logger = logging.getLogger(__name__)

TaskLock = threading.Lock()

ExecutingLock = threading.Lock()
ExecutingItemTasks: Dict[str, Task] = {}

StopLock = threading.Lock()
StopFlags: Dict[str, bool] = {}


class EnvCheckTask:
    TASK_TIME_OUT = 1200

    def __init__(self, request_data: Optional[Dict] = None, task_id: str = ""):
        self.task_info = request_data
        self.task_id = task_id
        self.task_repository = env_check_repository.EnvCheckTaskRepository()
        self.item_repository = env_check_repository.EnvCheckItemRepository()
        self.node_repository = env_check_repository.EnvCheckNodeRepository()
        self.result_repository = env_check_repository.EnvCheckResultRepository()

    def is_param_hidden(self, check_item, param, hidden_info) -> bool:
        if len(hidden_info) == 0:
            return False
        for item in hidden_info:
            compare_key = item.get("compare_key", "").replace(
                f"{check_item}.", "")
            value = param.get(compare_key)
            compare_values = item.get("compare_values", [])
            compare_include = item.get("compare_include", False)
            is_include = value in compare_values
            if (compare_include and not is_include) or (not compare_include and is_include):
                return False
        return True

    def _validate_item_params(self):
        item_configs = files.get_env_check_item_config()
        if not item_configs:
            raise Exception("Empty env check item config")
        for item in self.task_info.get("items", []):
            check_item = item.get("check_item")
            if not check_item:
                continue
            param = item.get("param", {})
            item_config = item_configs.get(check_item)
            if not item_config:
                raise Exception(
                    f"Check item not found in config file: {check_item}")
            params_config = item_config.get("param")
            if not params_config:
                logger.info(f"Check item has no params: {check_item}")
                continue
            for param_config in params_config:
                if self.is_param_hidden(check_item, param, param_config.get("hidden", [])):
                    continue
                required = param_config.get("required")
                param_config_key = param_config.get("key")
                param_value = param.get(param_config_key)
                if required and param_value is None:
                    raise Exception(f"Param is required: {param_config_key}")
                if param_value is None:
                    continue
                value_type_config = param_config.get("value_type")
                if value_type_config is None:
                    continue
                if value_type_config == "string":
                    if not isinstance(param_value, str):
                        raise Exception(
                            f"Param value type is wrong: {param_config_key} value type should be {value_type_config}"
                        )
                    if required and param_value == "":
                        raise Exception(
                            f"Param value is required: {param_config_key}")

                elif value_type_config == "number":
                    if not tools.is_number(param_value):
                        raise Exception(
                            f"Param value type is wrong: {param_config_key} value type should be {value_type_config}"
                        )
                    min_value = param_config.get("min")
                    if min_value is None:
                        continue
                    if isinstance(param_value, float):
                        if float(param_value) < float(min_value):
                            raise Exception(
                                f"Param value is wrong: {param_config_key} value {param_value} should >= {min_value}"
                            )
                    elif int(param_value) < int(min_value):
                        raise Exception(
                            f"Param value is wrong: {param_config_key} value {param_value} should >= {min_value}"
                        )
                elif value_type_config == "selector":
                    selector_options = param_config.get("selector_option")
                    if not selector_options:
                        continue
                    in_selector = False
                    for option in selector_options:
                        if isinstance(option, dict):
                            if param_value == option.get("value"):
                                in_selector = True
                                break
                        elif param_value == option:
                            in_selector = True
                            break
                    if not in_selector:
                        raise Exception(
                            f"Param value is wrong: {param_config_key} value {param_value} not in {selector_options}"
                        )

    def _validate_nodes(self):
        nodes = self.task_info.get("nodes", [])
        if len(nodes) == 0:
            raise Exception("no node selected")

    def _validate_items(self):
        for item in self.task_info.get("items", []):
            check_item = item.get("check_item")
            task_cls = get_task_by_check_item(check_item)
            if not task_cls:
                raise Exception(f"Not support check item: {check_item}")
            task_cls.validate(self.task_info)

    def _validate_create_info(self):
        task_name = self.task_info.get("task_name")
        if not validate_task_name(task_name):
            raise Exception(f"Invalid task name: {task_name}")
        self._validate_nodes()
        self._validate_items()
        self._validate_item_params()

    def create(self):
        if not self.task_info:
            raise ValueError("The task info is empty.")
        logger.info(f"Begin create check task: {self.task_info}")
        self._validate_create_info()
        self.env_check_task = self.task_repository.create(
            task_name=self.task_info.get("task_name"),
            task_type=self.task_info.get("task_type"),
            nodes=self.task_info.get("nodes", []),
            description=self.task_info.get("description", ""),
        )
        for item in self.task_info.get("items", []):
            self.item_repository.create(
                task=self.env_check_task,
                parent=item.get("parent"),
                check_item=item.get("check_item"),
                param=item.get("param", {}),
            )
        if self.env_check_task.task_type == TaskType.BASIC.value:
            for node_id in self.env_check_task.nodes:
                self.node_repository.create(
                    task=self.env_check_task,
                    node_id=node_id,
                )

    def _set_task_executing_item(self, item_task: Task):
        with ExecutingLock:
            ExecutingItemTasks[self.task_id] = item_task

    def _get_task_executing_item(self) -> Task:
        with ExecutingLock:
            return ExecutingItemTasks.get(self.task_id, None)

    def _remove_task_executing_item(self):
        with ExecutingLock:
            if ExecutingItemTasks.get(self.task_id, None) is not None:
                del ExecutingItemTasks[self.task_id]

    def _set_task_stop_flag(self, stopped: bool):
        with StopLock:
            StopFlags[self.task_id] = stopped

    def _get_task_stop_flag(self) -> bool:
        with StopLock:
            return StopFlags.get(self.task_id, None)

    def _remove_task_stop_flag(self):
        with StopLock:
            if StopFlags.get(self.task_id, None) is not None:
                del StopFlags[self.task_id]

    def _execute_item(self, item: models.EnvCheckItem):
        task_cls = get_task_by_check_item(item.check_item)
        if not task_cls:
            raise Exception(f"Not support check item: {item.check_item}")
        node_ids = self.env_check_task.nodes
        if not node_ids:
            raise Exception("Empty nodes specified")
        # sort
        repository = node_repository.NodeRepository()
        existing_nodes = repository.find_by_ids(node_ids).order_by(
            Case(*[When(id=id_val, then=pos)
                 for pos, id_val in enumerate(node_ids)])
        )
        if len(set(node_ids)) != len(existing_nodes):
            existing_ids = set(node.id for node in existing_nodes)
            missing_ids = set(node_ids) - set(existing_ids)
            raise Exception(f"Unknown node ids {missing_ids}")
        task_nodes_info = []
        for n in existing_nodes:
            task_nodes_info.append(
                NodeInfo(
                    # n.id is UUID('db8fb1e6-48f1-4262-b15c-d376072e6d1c')
                    node_id=tools.change_model_item_to_str(n.id),
                    node_name=n.node_name,
                    gpu_manufacturer=n.gpu_manufacturer,
                    gpu_type=n.gpu_type,
                    gpu_count=n.gpu_count,
                    username=n.username,
                    ip_address=n.ip_address,
                    port=n.port,
                    ssh_password=n.ssh_password,
                )
            )
        task_options = TaskOptions(
            timeout=self.TASK_TIME_OUT,
            nodes=task_nodes_info,
            task_params=item.param,
        )
        task_obj: Task = task_cls()
        task_obj.env_check_item = item
        task_obj.task_options = task_options
        self._set_task_executing_item(task_obj)
        item.status = TaskStatus.INPROGRESS.value
        item.set_start_time()
        self.item_repository.save(item)
        task_obj.execute()
        self._remove_task_executing_item()

    def clean_task_history(self):
        self._remove_task_executing_item()
        self._remove_task_stop_flag()
        self.env_check_task.status = TaskStatus.ACCEPTED.value
        self.env_check_task.msg = ""
        self.env_check_task.start_time = None
        self.env_check_task.end_time = None
        self.task_repository.save(self.env_check_task)
        for item in self.item_repository.find_all(self.env_check_task.id):
            item.status = TaskStatus.ACCEPTED.value
            item.msg = ""
            item.start_time = None
            item.end_time = None
            self.item_repository.save(item)
        for node in self.node_repository.find_all(self.env_check_task.id):
            node.status = TaskStatus.ACCEPTED.value
            node.msg = ""
            node.start_time = None
            node.end_time = None
            self.node_repository.save(node)
        self.result_repository.delete_all(self.env_check_task)

    def _execute_items(self):
        try:
            for item in self.item_repository.find_all(self.env_check_task.id):
                if not self._get_task_stop_flag():
                    self._execute_item(item)
                else:
                    self._remove_task_stop_flag()
                    break
        except Exception as e:
            logger.error(f"Exception: {e}")
            self.env_check_task.status = TaskStatus.FAILED.value
            self.env_check_task.msg = f"Exception: {e}"
            self.env_check_task.set_end_time()
            self.task_repository.save(self.env_check_task)
            self._sync_executing_nodes_items_finished_status(
                TaskStatus.FAILED.value, f"Exception: {e}"
            )
        finally:
            self._remove_task_executing_item()

    def execute(self):
        if not self.task_id:
            raise ValueError("The task id is empty.")
        with TaskLock:
            self.env_check_task = self.task_repository.find_by_id(self.task_id)
            if self.env_check_task.status in TASK_RUNNING_STATUS:
                msg = f"The task {self.env_check_task.task_name} is running, please wait!"
                raise Exception(msg)
            not_finished = self.task_repository.find_by_statuses(
                TASK_RUNNING_STATUS)
            if not_finished:
                conflicted_tasks = [
                    task.task_name
                    for task in not_finished
                    if len(tools.get_src_in_dst_list(self.env_check_task.nodes, task.nodes)) > 0
                ]
                if len(conflicted_tasks) > 0:
                    msg = f"Tasks {conflicted_tasks} are running, contains conflicted nodes, please wait!"
                    raise Exception(msg)
            self.clean_task_history()
            self.env_check_task.status = TaskStatus.INPROGRESS.value
            self.env_check_task.set_start_time()
            self.task_repository.save(self.env_check_task)
        logger.info(
            f"Begin execute check task: {self.env_check_task.task_name}")
        try:
            if self.env_check_task.task_type == TaskType.BASIC.value:
                for node in self.node_repository.find_all(self.env_check_task.id):
                    node.status = TaskStatus.INPROGRESS.value
                    node.set_start_time()
                    self.node_repository.save(node)
            threading.Thread(target=self._execute_items, daemon=True).start()
        except Exception as e:
            self.env_check_task.status = TaskStatus.FAILED.value
            self.env_check_task.msg = f"Exception: {e}"
            self.env_check_task.set_end_time()
            self.task_repository.save(self.env_check_task)
            self._sync_executing_nodes_items_finished_status(
                TaskStatus.FAILED.value, f"Exception: {e}"
            )
            raise e

    def modify(self):
        if not self.task_id:
            raise ValueError("The task id is empty.")
        with TaskLock:
            self.env_check_task = self.task_repository.find_by_id(self.task_id)
            if self.env_check_task.status in TASK_RUNNING_STATUS:
                msg = f"The task {self.env_check_task.task_name} is running, please wait!"
                raise Exception(msg)

            self._validate_item_params()
            for item in self.task_info.get("items", []):
                item_id = item.get("item_id")
                if not item_id:
                    continue
                param = item.get("param", {})
                for env_check_item in self.item_repository.find_by_id(self.env_check_task.id, item_id):
                    env_check_item.param = param
                    self.item_repository.save(env_check_item)
            self.clean_task_history()
            self.env_check_task.status = TaskStatus.ACCEPTED.value
            self.task_repository.save(self.env_check_task)

    def stop(self):
        if not self.task_id:
            raise ValueError("The task id is empty.")
        with TaskLock:
            self.env_check_task = self.task_repository.find_by_id(self.task_id)
            if self.env_check_task.status not in TASK_EXECUTING_STATUS:
                msg = f"The task {self.env_check_task.task_name} status is {self.env_check_task.status}, not allowned to stop"
                raise Exception(msg)
            self.env_check_task.status = TaskStatus.STOPPING.value
            self.task_repository.save(self.env_check_task)
        self._set_task_stop_flag(True)
        logger.info(f"Check task: {self.env_check_task.task_name} is Stopping")
        try:
            # notify item task thread to stop
            item_task = self._get_task_executing_item()
            if item_task is not None:
                logger.info(f"Current executing item: {item_task}, will stop")
                item_task.stop()
            self._sync_executing_nodes_items_finished_status(
                TaskStatus.STOPPED.value, "Stopped by user"
            )
        except Exception as e:
            self.env_check_task.status = TaskStatus.FAILED.value
            self.env_check_task.msg = f"Exception: {e}"
            self.env_check_task.set_end_time()
            self.task_repository.save(self.env_check_task)
            raise e
        self.env_check_task.status = TaskStatus.STOPPED.value
        self.env_check_task.set_end_time()
        self.env_check_task.msg = "Stopped by user"
        self.task_repository.save(self.env_check_task)
        logger.info(f"Check task: {self.env_check_task.task_name} stopped")

    def _sync_executing_nodes_items_finished_status(
        self, finished_status, msg: Optional[str] = None
    ):
        if self.env_check_task.task_type == TaskType.BASIC.value:
            for node in self.node_repository.find_by_statuses(
                self.env_check_task.id,
                TASK_EXECUTING_STATUS
            ):
                node.status = finished_status
                if msg is not None:
                    node.msg = msg
                node.set_end_time()
                self.node_repository.save(node)
        for item in self.item_repository.find_by_statuses(self.env_check_task.id, TASK_EXECUTING_STATUS):
            item.status = finished_status
            if msg is not None:
                item.msg = msg
            item.set_end_time()
            self.item_repository.save(item)
