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
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.consts import TaskStatus
    from utils.consts import TaskResult
    from system_management.nodes.node_info import NodeInfo
except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.consts import TaskStatus
    from utils.consts import TaskResult
    from system_management.nodes.node_info import NodeInfo

logger = logging.getLogger(__name__)


class CheckGpuInfoTask(Task):
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="gpu_info_check",
    )

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check gpu info..."
            )
            logger.info("Start exec check gpu info...")

            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected")
                logger.error("no node selected")
                return

            node_ids = {}
            nodeInfos = []
            for node in self.task_options.nodes:
                nodeInfos.append(
                    NodeInfo(node.ip_address, node.username,
                             node.ssh_password, node.port, True)
                )
                node_ids[node.ip_address] = node.node_id
            with ThreadPoolExecutor(max_workers=len(nodeInfos)) as executor:
                futures = []
                for node in nodeInfos:
                    futures.append(executor.submit(node.get_gpu_info))
                # wait all tasks completed
                for future in as_completed(futures):
                    future.result()

            self._handle_result(nodeInfos, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check gpu info exception: {e}")

    def _handle_result(self, node_infos, node_ids):
        gpu_model = self.task_options.task_params.get("gpu_model")
        gpu_count = self.task_options.task_params.get("gpu_count")
        abnormal_host = []
        for node_info in node_infos:
            logger.info(
                f"{node_info.ip_address}: GPU model: {node_info.gpu_type}, GPU count: {node_info.gpu_count}"
            )
            detail_result = [
                f"GPU model: {node_info.gpu_type}",
                f"GPU count: {node_info.gpu_count}",
            ]
            format_result = {
                "result_type": "table",
                "data": [["Item", "Actual", "Expected", "Result"]],
            }
            check_gpu_model = node_info.gpu_type
            check_gpu_count = node_info.gpu_count
            is_gpu_model_ok = False
            is_gpu_count_ok = False
            if check_gpu_model == gpu_model:
                is_gpu_model_ok = True
            if check_gpu_count == gpu_count:
                is_gpu_count_ok = True
            format_result["data"].append(
                [
                    "GPU Model",
                    check_gpu_model,
                    gpu_model,
                    (TaskResult.NORMAL.value if is_gpu_model_ok else TaskResult.ABNORMAL.value),
                ]
            )
            format_result["data"].append(
                [
                    "GPU Count",
                    check_gpu_count,
                    gpu_count,
                    (TaskResult.NORMAL.value if is_gpu_count_ok else TaskResult.ABNORMAL.value),
                ]
            )
            status = (
                TaskStatus.SUCCESS.value
                if is_gpu_model_ok and is_gpu_count_ok
                else TaskStatus.FAILED.value
            )
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(node_info.ip_address)
            detail_result.append(node_info.ip_address + " exec " + status)
            detail_result.append(
                f"GPU model {'normal' if is_gpu_model_ok else 'abnormal'}")
            detail_result.append(
                f"GPU count {'normal' if is_gpu_count_ok else 'abnormal'}")
            node_id = node_ids.get(node_info.ip_address)
            self.save_check_result_progress(
                [node_id],
                status,
                node_info.ip_address + " exec " + status,
                detail_result,
                [format_result],
                self.sync_check_node,
            )
        msg = ""
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value
        self.save_check_item_progress(status, msg)
