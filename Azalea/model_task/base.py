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

import configparser
from typing import Dict
from typing import List
from typing import Optional
from dataclasses import dataclass
from dataclasses import field
from numexpr import evaluate
import os
import yaml
import logging
import time
import threading
import json
import re

from inspector import models
from inspector.repository import node_repository
from utils.ssh_tool import HostOutputData
from utils.ssh_tool import exec_cmd_on_single_host
from utils.ssh_tool import copy_file_to_single_node
from utils import decryption, tools
from utils.consts import PathConfig
from inspector.repository.model_task_repository import ModelTaskRepository, NodeModelTaskRepository


logger = logging.getLogger(__name__)

RUNNING_STATUS = ["in_progress", "stopping"]
EXECUTING_STATUS = ['in_progress']
CONFIG = configparser.ConfigParser()
CONFIG.read(PathConfig.ETC_FILE)
FILE_DISTRIBUTION_MAX_PARALLEL = int(
    CONFIG.get("model_test", "file_distribution_max_parallel", fallback="5"))
THREAD_LOCK = threading.Lock()
SEMAPHORE = threading.Semaphore(FILE_DISTRIBUTION_MAX_PARALLEL)


EXCEPTION_PATTERN = r'exception:\s*(.*)'


@dataclass
class NodeOptions:
    task_type: str
    task_action: str
    target_result: Dict[str, str] = field(default_factory=dict)
    task_param: Dict[str, str] = field(default_factory=dict)


class ModelTask(object):
    PSSH_EXEC_TIMEOUT = 60

    def __init__(self, task_info: Dict, action: str = "create"):
        self.repository = ModelTaskRepository()
        self.node_repository = NodeModelTaskRepository()
        self.task_action = action
        if action == "execute":
            logger.info(f"Re-running model task: {task_info}")
            self._init_task_info_for_execute(task_info)
        elif action == "restore":
            logger.info(f"Restore model task: {task_info}")
            self._init_task_info_for_restore(task_info)
        else:
            logger.info(f"New model task: {task_info}")
            self._init_task_info_for_create(task_info)

    def _init_task_info_for_create(self, task_info: dict):
        self.model_task = self.repository.create(
            task_name=task_info.get("task_name"),
            task_type=task_info.get("task_type"),
            remote_data_path=task_info.get("remote_data_path")
        )
        self.node_model_tasks = []
        self.node_threads = []
        self._get_node_model_tasks(task_info.get("node_infos", []))

    def _init_task_info_for_execute(self, task_info: Dict):
        task_id = task_info.get("task_id")
        node_infos = task_info.get("node_infos", [])
        self.model_task = self.repository.find_by_id(task_id)
        if not self.model_task:
            raise ValueError(f"No task found with ID {task_id}")
        if self.model_task.status in RUNNING_STATUS:
            raise Exception(f"Task {task_id} is {self.model_task.status}, "
                            f"not allowed to executed!")
        node_tasks = self.node_repository.find_all(task_id)
        self.node_model_tasks = []
        for node_task in node_tasks:
            new_target_result = self._get_node_target_result(
                node_infos, tools.change_model_item_to_str(node_task.node.id))
            if new_target_result is None:
                new_target_result = node_task.target_result or {}
            node_options = NodeOptions(
                task_type=node_task.task_type,
                target_result=new_target_result,
                task_action=self.task_action,
                task_param=node_task.task_param
            )
            node_model_task = NodeModelTask(
                self.model_task, node_task.node, node_options, node_task)
            self.node_model_tasks.append(node_model_task)
        self.clean_task_history()

    def _init_task_info_for_restore(self, task_info: dict):
        task_id = task_info.get("task_id")
        self.model_task = self.repository.find_by_id(task_id)
        if not self.model_task:
            raise ValueError(f"No task found with ID {task_id}")
        if self.model_task.status not in EXECUTING_STATUS:
            raise Exception(f"Task {task_id} is {self.model_task.status}, "
                            f"not need to restore!")
        node_tasks = self.node_repository.find_all(task_id)
        self.node_model_tasks = []
        for node_task in node_tasks:
            node_options = NodeOptions(
                task_type=node_task.task_type,
                target_result=node_task.target_result,
                task_action=self.task_action,
                task_param=node_task.task_param
            )
            node_model_task = NodeModelTask(
                self.model_task, node_task.node, node_options, node_task)
            self.node_model_tasks.append(node_model_task)

    def clean_task_history(self):
        self.model_task.start_time = None
        self.model_task.end_time = None
        self.model_task.status = "accepted"
        self.repository.save(self.model_task)

    @staticmethod
    def _get_node_target_result(node_infos: List[Dict],
                                node_id: str) -> Dict:
        for node_info in node_infos:
            if node_info.get("node_id") == node_id:
                return node_info.get('target_result', None)
        return None

    def _get_node_model_tasks(self, node_info: List[Dict]):
        try:
            for node in node_info:
                node_id = node.get("node_id")
                n_repository = node_repository.NodeRepository()
                node_obj = n_repository.find_by_id(node_id)
                if not node_obj:
                    raise ValueError(f"Unknown node {node_id} for "
                                     f"{self.model_task.task_name}")

                node_options = NodeOptions(
                    task_type=node.get("task_type"),
                    target_result=node.get("target_result", {}),
                    task_action=self.task_action,
                    task_param=node.get("task_param", {})
                )
                node_model_task = NodeModelTask(
                    self.model_task, node_obj, node_options)
                self.node_model_tasks.append(node_model_task)
        except Exception as e:
            self.model_task.status = "failed"
            self.repository.save(self.model_task)
            raise Exception(f"get node model task failed: {e}")

    def execute(self):
        if self.task_action != "restore":
            logger.info(f"Task {self.model_task.task_name} start")
            self.model_task.status = "in_progress"
            self.model_task.set_start_time()
            self.repository.save(self.model_task)
        for task in self.node_model_tasks:
            th = threading.Thread(target=task.execute)
            th.setDaemon(True)
            th.start()


class NodeModelTask(object):
    PSSH_EXEC_TIMEOUT = 60

    def __init__(self, task: models.ModelTask, node: models.Node,
                 node_options: NodeOptions,
                 node_task: Optional[models.NodeModelTask] = None):
        try:
            self.repository = ModelTaskRepository()
            self.node_repository = NodeModelTaskRepository()
            self.task = task
            self.node = node
            self.node_options = node_options
            self.remote_data_path = os.path.join(
                task.remote_data_path, tools.change_model_item_to_str(task.id))
            if node_task:
                self.node_model_task = node_task
            else:
                self.node_model_task = models.NodeModelTask(
                    node=node,
                    task=task,
                    task_type=node_options.task_type,
                    target_result=node_options.target_result,
                    task_param=node_options.task_param
                )
                self.node_repository.save(self.node_model_task)

            if node_options.task_action != "restore":
                self.clean_node_history()
                self.task_info = self.load_task_info_from_yml()
                self.save_task_info()
            else:
                self.task_info = self.node_model_task.task_info

            logger.info(f"Initialized task for {node.ip_address} successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize task for {node.ip_address}: {e}")
            raise RuntimeError(
                f"Failed to initialize task for {node.ip_address}: {e}")

    def clean_node_history(self):
        self.node_model_task.finished_steps = []
        self.node_model_task.start_time = None
        self.node_model_task.progress = 0
        self.node_model_task.status = "accepted"
        self.node_model_task.target_result = self.node_options.target_result
        self.node_model_task.task_result = {}
        self.node_model_task.end_time = None
        self.node_repository.save(self.node_model_task)

    def save_task_info(self):
        self.node_model_task.task_info = self.task_info
        self.node_repository.save(self.node_model_task)
        logger.info(f"{self.task.task_name} info on "
                    f"{self.node.ip_address}: "
                    f"{self.node_model_task.task_info}")

    def get_task_time_info(self, task_info) -> Dict:
        try:
            timeout_expression = task_info.get("task_timeout", "0")
            task_timeout = str(timeout_expression).format(
                **task_info.get("params", {}))
            timeout = evaluate(task_timeout).item()
        except Exception as e:
            logger.warn(f"parse timeout failed {str(e)}")
            timeout = 0
        try:
            estimated_time_expression = task_info.get(
                "task_estimated_time", "0")
            task_estimated_time = str(estimated_time_expression).format(
                **task_info.get("params", {}))
            estimated_time = evaluate(task_estimated_time).item()
        except Exception as e:
            logger.warn(f"parse estimated time failed {str(e)}")
            estimated_time = 0
        return {
            "timeout": timeout,
            "estimated_time": estimated_time
        }

    def load_task_info_from_yml(self) -> Dict:
        try:
            with open(PathConfig.MODEL_TESTING_CONFIG_YML, 'r', encoding='utf-8') as f:
                model_tasks = yaml.safe_load(f)
            task_info = model_tasks.get(
                self.node_options.task_type, {}).get(
                self.node.gpu_manufacturer, {}).get(
                self.node.gpu_type)
            if not task_info:
                raise ValueError(f"Unsupported task type "
                                 f"{self.node_options.task_type} on "
                                 f"{self.node.gpu_manufacturer} "
                                 f"{self.node.gpu_type}")
            task_info["params"] = task_info.get("params", {})
            task_info["params"].update({
                "gpu_manufacturer": self.node.gpu_manufacturer,
                "gpu_type": self.node.gpu_type,
                "task_type": self.node_options.task_type,
                "task_name": self.task.task_name,
                "task_id": tools.change_model_item_to_str(self.task.id),
                "node_name": self.node.node_name,
                "node_id": tools.change_model_item_to_str(self.node.id),
                "remote_data_path": self.remote_data_path,
                "docker_name": f"azalea_"
                               f"{self.node.gpu_manufacturer}_"
                               f"{self.node.gpu_type}_"
                               f"{self.node_options.task_type}_"
                               f"{self.task.task_name}"
            })
            if self.node_options.task_param is not None:
                task_info["params"].update(self.node_options.task_param)
            task_info["params"].update(self.get_task_time_info(task_info))
            logger.info(f"Model task info from YAML: {task_info}")
            return task_info
        except Exception as e:
            msg = f"Failed to load model task info " \
                  f"from {PathConfig.MODEL_TESTING_CONFIG_YML}: {e}"
            self.save_node_progress("failed", msg)
            raise RuntimeError(msg)

    def save_task_progress(self):
        with THREAD_LOCK:
            node_tasks = self.node_repository.find_all(self.task.id)
            finished_nodes = {
                node_task.node.id: node_task.status
                for node_task in node_tasks
                if node_task.status in ["failed", "success", "stopped"]
            }
            if len(finished_nodes) == len(node_tasks):
                if "failed" in finished_nodes.values():
                    self.task.status = "failed"
                elif self.task.status != "stopping":
                    self.task.status = "success"
                else:
                    self.task.status = "stopped"
                logger.info(f"Task {self.task.task_name} end, "
                            f"status: {self.task.status}")
                self.task.set_end_time()
                self.repository.save(self.task)

    def save_node_progress(self, status: str, msg: str = "",
                           progress: Optional[int] = None,
                           finished_step: Optional[str] = None,
                           task_result: Optional[Dict] = None):
        if status != self.node_model_task.status:
            logger.info(f"{self.node_options.task_type} on "
                        f"{self.node.ip_address} status: "
                        f"{self.node_model_task.status} -> {status}")
        if msg and msg != self.node_model_task.msg:
            logger.info(f"{self.node_options.task_type} on "
                        f"{self.node.ip_address} message: {msg}")
        self.node_model_task.status = status
        self.node_model_task.msg = msg
        if progress is not None \
                and self.node_model_task.progress != int(progress):
            logger.info(f"{self.node_options.task_type} on "
                        f"{self.node.ip_address} progress: "
                        f"{self.node_model_task.progress} -> {progress}")
            self.node_model_task.progress = int(progress)
        if finished_step \
                and finished_step not in self.node_model_task.finished_steps:
            self.node_model_task.finished_steps.append(finished_step)
        if task_result:
            self.node_model_task.task_result = task_result
            logger.info(f"{self.node_options.task_type} on "
                        f"{self.node.ip_address} result: {task_result}")
        elif status in ["failed", "success", "stopped"]:
            self.node_model_task.set_end_time()
        self.node_repository.save(self.node_model_task)
        if status in ["failed", "success", "stopped"]:
            self.save_task_progress()

    def check_step_is_run(self, step_name):
        """
        检查指定步骤是否已经执行。
        :param step_name: 需要检查的步骤名称
        :return: 步骤是否已执行 (bool)
        """
        if step_name in self.node_model_task.finished_steps:
            logger.info(f"{step_name} on {self.node.ip_address} "
                        f"is already run, skip...")
            return True
        return False

    def check_task_is_stopping(self, step_name):
        self.task = self.repository.find_by_id(self.task.id)
        if self.task.status == "stopping":
            if step_name != "execute_post":
                logger.info(f"{self.task.task_name} on {self.node.ip_address} "
                            f"is stopping, skip {step_name}")
                self.save_node_progress("stopping")
            return True
        return False

    def execute_cmd(self, cmd: str, log_level="info") -> HostOutputData:
        try:
            if log_level == "debug":
                logger.debug(f"execute {cmd} on {self.node.ip_address}")
            else:
                logger.info(f"execute {cmd} on {self.node.ip_address}")
            output = exec_cmd_on_single_host(
                self.node.username, self.node.ip_address,
                self.node.ssh_password,
                cmd,
                port=self.node.port,
                timeout=self.PSSH_EXEC_TIMEOUT
            )
        except Exception as e:
            error_msg = f"execute {cmd} on {self.node.ip_address} failed: {e}"
            logger.error(error_msg)
            output = HostOutputData(
                host=self.node.ip_address,
                exit_code=-1,
                std_out=[],
                std_err=[str(e)]
            )
        return output

    def distribute_file(self, local_file: str, remote_file: str):
        copy_file_to_single_node(
            self.node.username, self.node.ip_address,
            self.node.ssh_password,
            local_file, remote_file,
            port=self.node.port
        )

    def distribute_model_files(self):
        step_name = "distribute_files"
        if self.check_task_is_stopping(step_name):
            return
        if self.check_step_is_run(step_name):
            return
        with SEMAPHORE:
            self.save_node_progress(
                "in_progress",
                f"Start to distributed files to {self.node.ip_address}."
            )
            for file in self.task_info.get("scp_file", []):
                try:
                    file_name = os.path.basename(file)
                    remote_path = os.path.join(
                        self.remote_data_path, file_name)
                    self.distribute_file(file, remote_path)
                except Exception as e:
                    msg = f"Failed to upload {file} to " \
                          f"{self.node.ip_address}: {e}"
                    raise RuntimeError(msg)
        self.save_node_progress(
            "in_progress",
            f"Distributed files to {self.node.ip_address} successfully",
            finished_step=step_name
        )

    def start_task(self):
        try:
            step_name = "start_task"
            if self.check_task_is_stopping(step_name):
                return
            if self.check_step_is_run(step_name):
                return
            self.save_node_progress(
                "in_progress", f"Start task on {self.node.ip_address}", 10)
            for cmd in self.task_info.get("task_cmd", []):
                exec_cmd = cmd.format(**self.task_info.get("params", {}))
                output = self.execute_cmd(exec_cmd)
                if output.exit_code != 0:
                    msg = f"Failed to run task when executing {exec_cmd}, " \
                          f"error code: {output.exit_code}, " \
                          f"error msg: {output.std_err}"
                    raise RuntimeError(msg)
        except Exception as e:
            msg = f"Failed to start task on {self.node.ip_address}: {e}"
            raise RuntimeError(msg)
        self.save_node_progress(
            "in_progress", f"Started task on {self.node.ip_address}",
            finished_step=step_name
        )

    def check_progress(self) -> int | None:
        exception_match = None
        try:
            progress_cmd = self.task_info.get("progress", "")
            cmd = progress_cmd.format(**self.task_info.get("params", {}))
            output = self.execute_cmd(cmd, log_level="debug")
            if output.exit_code == 0 and output.std_out:
                exception_match = re.match(
                    EXCEPTION_PATTERN, output.std_out[0])
                if exception_match:
                    exception_message = exception_match.group(1).strip()
                    self.save_node_progress("failed", exception_message)
                    raise RuntimeError(exception_message)
                return int(output.std_out[0])
        except Exception as e:
            logger.error(f"get progress on {self.node.ip_address} failed: {e}")
            if exception_match:
                raise RuntimeError(e)
        return None

    def check_finished(self):
        step_name = "check_finished"
        if self.check_task_is_stopping(step_name):
            return
        if self.check_step_is_run(step_name):
            return
        params = self.task_info.get("params", {})
        timeout = params.get("timeout", 0) * 60
        query_interval = params.get("query_interval", 5) * 60
        start_time = time.time()
        while time.time() - start_time < timeout or timeout <= 0:
            if self.check_task_is_stopping(step_name):
                return
            progress = self.check_progress()
            if progress == 100:
                msg = f"Finished executing {self.node_options.task_type} " \
                      f"on {self.node.ip_address}."
                self.save_node_progress(
                    "in_progress", msg, 99, step_name)
                return
            msg = f"{self.node_options.task_type} " \
                  f"on {self.node.ip_address} is executing."
            self.save_node_progress("in_progress", msg, progress)
            time.sleep(query_interval)
        msg = f"{self.node_options.task_type}" \
              f" on {self.node.ip_address} has timed out."
        raise TimeoutError(msg)

    @staticmethod
    def to_float(value):
        try:
            return float(value)
        except Exception:
            return value

    def get_indicator_result(self, task_value, target_value, indicator_name):
        """
        Evaluate the status of an indicator based on
        its value and target constraints.

        :param task_value: The actual value of the indicator.
        :param target_value: A dictionary containing 'max'
               and/or 'min' constraints.
        :param indicator_name: The name of the indicator.
        :return: A dictionary with the indicator's value and
                status ('normal' or 'abnormal').
        """
        try:
            status = ""
            indicator_value = self.to_float(task_value)
            if target_value.get("equal") is not None:
                status = "normal" if indicator_value == target_value["equal"] else "abnormal"
            elif target_value.get("max") is not None and target_value.get("min") is not None:
                status = "normal" if indicator_value <= float(
                    target_value["max"]) and indicator_value >= float(target_value["min"]) else "abnormal"
            elif target_value.get("max") is not None:
                status = "normal" if indicator_value <= float(
                    target_value["max"]) else "abnormal"
            elif target_value.get("min") is not None:
                status = "normal" if indicator_value >= float(
                    target_value["min"]) else "abnormal"

            return {"value": indicator_value, "status": status}
        except Exception as e:
            logger.error(
                f"get {indicator_name} on {self.node.ip_address} failed: {e}")
            return {"value": indicator_value, "status": "abnormal"}

    def check_task_result(self):
        """
        Check the result of a task and update the node's progress accordingly.

        :return: The overall status of the task ('success' or 'failed').
        """
        step_name = "check_task_result"
        if self.check_task_is_stopping(step_name):
            return
        if self.check_step_is_run(step_name):
            for indicator_name, result \
                    in self.node_model_task.task_result.items():
                if result.get("status", "abnormal") == "abnormal":
                    return "failed"
            return "success" if self.node_options.target_result else "failed"

        self.save_node_progress(
            "in_progress", "Start to get model task result.")
        status = "success"
        task_result = {}
        target_result = self.node_options.target_result
        for indicator_name in target_result.keys():
            task_result[indicator_name] = \
                {"value": "", "status": "abnormal"}
        result_cmd = self.task_info.get("result", "")

        try:
            exec_cmd = result_cmd.format(**self.task_info.get("params", {}))
            output = self.execute_cmd(exec_cmd)
            if output.exit_code != 0 or not output.std_out:
                logger.error(f"Failed to get task result "
                             f"by {exec_cmd} after model task.")
                status = "failed"
            else:
                output_result = json.loads(output.std_out[0])
                for indicator_name, task_value in output_result.items():
                    target_value = target_result.get(indicator_name, {})
                    indicator_result = self.get_indicator_result(
                        task_value, target_value, indicator_name)
                    if indicator_result.get("status", "") == "abnormal":
                        status = "failed"
                    task_result[indicator_name] = indicator_result
        except Exception as e:
            status = "failed"
            error_msg = f"get model task result on " \
                        f"{self.node.ip_address} failed: {e}"
            logger.error(error_msg)

        self.save_node_progress(
            "in_progress",
            "Finished getting model task result.", 99, step_name, task_result
        )
        return status

    def execute_pre(self):
        step_name = "execute_pre"
        if self.check_task_is_stopping(step_name):
            return

        # 检查步骤是否已经执行，如果已执行则直接返回
        if self.check_step_is_run(step_name):
            return

        # 保存节点进度为进行中
        self.save_node_progress(
            "in_progress", f"Task pre on {self.node.ip_address}")

        try:
            # 执行预处理命令
            for cmd in self.task_info.get("pre_cmd", []):
                exec_cmd = cmd.format(**self.task_info.get("params", {}))
                output = self.execute_cmd(exec_cmd)
                if output.exit_code != 0:
                    msg = f"{exec_cmd} failed, " \
                          f"error code: {output.exit_code}, " \
                          f"error msg: {output.std_err}"
                    raise RuntimeError(msg)
        except Exception as e:
            # 处理异常并记录失败状态
            msg = f"Failed to execute task pre on {self.node.ip_address}: {e}"
            raise RuntimeError(msg)
        # 如果所有命令都成功执行，更新进度为成功
        self.save_node_progress(
            "in_progress",
            f"Task pre on {self.node.ip_address} is successful.",
            finished_step=step_name
        )

    def execute_post(self, status):
        try:
            step_name = "execute_post"
            process_status = "stopping" \
                if self.check_task_is_stopping(step_name) else "in_progress"
            if self.check_step_is_run(step_name):
                return
            self.save_node_progress(
                process_status,
                f"Task post on {self.node.ip_address}"
            )
            for cmd in self.task_info.get("post_cmd", []):
                exec_cmd = cmd.format(**self.task_info.get("params", {}))
                output = self.execute_cmd(exec_cmd)
                if output.exit_code != 0:
                    msg = f"{exec_cmd} failed, " \
                          f"error code: {output.exit_code}, " \
                          f"error msg: {output.std_err}"
                    raise RuntimeError(msg)
        except Exception as e:
            msg = f"Failed to execute task post on {self.node.ip_address}: {e}"
            raise RuntimeError(msg)
        if process_status == "stopping":
            self.save_node_progress(
                "stopped",
                f"Clean for stop on {self.node.ip_address} successfully."
            )
        else:
            self.save_node_progress(
                status,
                f"Finished all steps of {self.task.task_name} "
                f"on {self.node.ip_address}.",
                100, step_name
            )

    def execute(self):
        try:
            if self.node_options.task_action != "restore":
                if self.is_node_running_task(self.node.id):
                    msg = f"Another task is executing " \
                        f"on {self.node.ip_address}"
                    raise RuntimeError(msg)
                else:
                    estimated_time = self.task_info.get(
                        "params", {}).get("estimated_time", 0)
                    self.node_model_task.set_start_time(estimated_time)
                    self.save_node_progress(
                        "in_progress", "Initialized node task successfully", 5)
            self.execute_pre()
            self.distribute_model_files()
            self.start_task()
            self.check_finished()
            check_status = self.check_task_result()
            self.execute_post(check_status)
        except Exception as e:
            self.save_node_progress("failed", str(e))

    def is_node_running_task(self, node_id, task_type=""):
        node_tasks = self.node_repository.find_by_statuses_and_id(
            node_id, RUNNING_STATUS, task_type)
        return len(node_tasks) != 0
