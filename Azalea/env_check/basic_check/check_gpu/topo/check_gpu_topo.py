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

import csv
import logging
import os
from typing import List
from pssh.config import HostConfig
from pssh.output import HostOutput
from utils.consts import PathConfig

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import GpuManufacturer, TaskStatus
    from utils.tools import natural_sort_key
except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime
    from utils.consts import GpuManufacturer, TaskStatus
    from utils.tools import natural_sort_key

current_dir = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)

CONNECT_WAY_LIST = frozenset(["P2P", "PIX", "PXB", "PHB", "NODE", "SYS"])

CSV_PATH = PathConfig.UPLOAD_COMMON_FILE_PATH / "gpu_topo.csv"

topo_cmds = {
    GpuManufacturer.NVIDIA.value: """
            nvidia-smi topo -m 2>/dev/null
            """,
}


class CsvOperator(object):
    def __init__(self):
        pass

    def get_csv_data(self):
        if not os.path.exists(CSV_PATH):
            raise Exception(f"{CSV_PATH} not exists.")
        csv_data = []
        with open(CSV_PATH, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                csv_data.append(row)
        return csv_data

    def read(self):
        """
        return_data:
        {
            "GPU0": {
                "GPU0": "P2P",
                ...
                "mlx5_9": "PIX"
            },
            ...
        }
        """
        csv_data = self.get_csv_data()
        gpu_id_list = [gpu_id.strip() for gpu_id in csv_data[0][1::]]
        return_data = dict((gpu_id, {}) for gpu_id in gpu_id_list)
        for data in csv_data[1::]:
            if not data:
                continue
            for idx, gpu_name in enumerate(return_data):
                return_data[gpu_name].update(
                    {data[0].strip(): data[idx + 1].strip()})
        return return_data


class ExtractData(object):
    def __init__(self, stdout):
        self.stdout = stdout
        self.process_data = (
            []
            if self.stdout is None
            else [
                data.replace("\t", " ").replace(
                    "\x1b[4m", " ").replace("\x1b[0m", " ").strip()
                for data in self.stdout
            ]
        )

    def extract_data(self):
        """
        return_data:
        {
            "GPU0": {
                "mlx5_8": "SYS",
                ...
                "mlx5_9": "PIX"
            },
            ...
        }
        """
        if not self.process_data:
            return {}
        gpu_id_list = self.get_all_gpus()
        return_data = dict((gpu_id, {}) for gpu_id in gpu_id_list)
        for line in self.process_data[1::]:
            if "Legend" in line:
                break
            if not line:
                continue
            line_list = [info for info in line.split(" ") if info]
            if "GPU" in line_list[0] or "XPU" in line_list[0]:
                continue
            new_line_list = self.deal_nic_no_space_conn_way(line_list)
            for idx, gpu_name in enumerate(return_data):
                return_data[gpu_name].update(
                    {new_line_list[0]: new_line_list[idx + 1]})
        return return_data

    def deal_nic_no_space_conn_way(self, line_list):
        """
        deal special situation:
        mlx5_9    SYS       SYS       SYS       SYS       NODE      NODE
        mlx5_bond_0SYS       SYS       SYS       SYS       NODE      NODE
        in this example, mlx5_bond_0SYS has no space between nic_name and SYS.
        """
        for conn_way in CONNECT_WAY_LIST:
            if conn_way in line_list[0]:
                new_line_list = line_list[1::]
                new_line_list.insert(0, conn_way)
                new_line_list.insert(0, line_list[0].replace(conn_way, ""))
                return new_line_list
        return line_list

    def get_all_gpus(self):
        if not self.process_data:
            return []

        return [
            gpu_id
            for gpu_id in self.process_data[0].split(" ")
            if "GPU" in gpu_id or "XPU" in gpu_id
        ]


class CheckGpuTopoTask(Task):
    PSSH_EXEC_TIMEOUT = 300
    sync_check_node = True

    metadata = TaskMetadata(
        check_item="gpu_topology_consistency_check",
    )

    @property
    def show_info(self):
        return {
            "actual_csv_gpu_diff": "-----gpu not consistent-----\n"
            "The query result shows the following gpus exist,but csv file not exist\n"
            "{}",
            "csv_actual_gpu_diff": "-----gpu not consistent-----\n"
            "csv file shows the following gpus exist,but the query result not exist:\n"
            "{}",
            "actual_csv_nic_diff": "-----nic not consistent-----\n"
            "The query result shows the following nics exist,but csv not exist:\n"
            "{}",
            "csv_actual_nic_diff": "-----nic not consistent-----\n"
            "csv file shows the following nics exist,but the query result not exist:\n"
            "{}",
        }

    def judge_gpu_nic_consistent(self, stdout_data, csv_data):
        actual_gpu_list = list(stdout_data.keys())
        actual_nic_list = list(stdout_data[actual_gpu_list[0]].keys())
        csv_gpu_list = list(csv_data.keys())
        csv_nic_list = list(csv_data[csv_gpu_list[0]].keys())
        actual_csv_gpu_diff = set(
            actual_gpu_list).difference(set(csv_gpu_list))
        csv_actual_gpu_diff = set(
            csv_gpu_list).difference(set(actual_gpu_list))
        actual_csv_nic_diff = set(
            actual_nic_list).difference(set(csv_nic_list))
        csv_actual_nic_diff = set(
            csv_nic_list).difference(set(actual_nic_list))
        return {
            "actual_csv_gpu_diff": actual_csv_gpu_diff,
            "csv_actual_gpu_diff": csv_actual_gpu_diff,
            "actual_csv_nic_diff": actual_csv_nic_diff,
            "csv_actual_nic_diff": csv_actual_nic_diff,
        }

    def judge_relation_consistent(self, stdout_data, csv_data):
        error_info = []

        for csv_gpu, csv_nic_relations in csv_data.items():
            # 检查实际环境中是否存在该 GPU和 NIC, 不存在，则跳过检查
            if csv_gpu not in stdout_data:
                continue
            for csv_nic, csv_relation in csv_nic_relations.items():
                if csv_nic not in stdout_data[csv_gpu]:
                    continue

                # 比较连接关系是否一致
                actual_relation = stdout_data[csv_gpu][csv_nic]
                if actual_relation != csv_relation:
                    msg = (
                        f"{csv_gpu}-{csv_nic} has an actual value {actual_relation}, "
                        f"where csv value is {csv_relation}."
                    )
                    error_info.append(msg)
        return error_info

    def execute(self) -> None:
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value, "Start exec check gpu topology..."
            )
            logger.info("Start exec check gpu topology...")

            host_ips = []
            host_config = []
            node_ids = {}
            host_args = []
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(user=node.username, port=node.port,
                               password=node.ssh_password)
                )
                node_ids[node.ip_address] = node.node_id
                host_args.append(topo_cmds.get(node.gpu_manufacturer, ""))

            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_ips,
                host_config,
                "%s",
                host_args=host_args,
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )
            logger.debug(host_output)
            self._handle_result(host_output, node_ids)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(f"Check gpu topology exception: {e}")

    def _handle_result(self, host_output, node_ids):
        # 判断 CSV 文件是否存在
        csv_exists = os.path.exists(CSV_PATH)
        csv_data = None
        if csv_exists:
            csv_data = CsvOperator().read()
            if not csv_data:
                logger.warning(
                    f"CSV file {CSV_PATH} data is empty. Please upload CSV file! Proceeding with topology query"
                )
            else:
                logger.info(
                    f"Found CSV file at {CSV_PATH}. Proceeding with topology comparison.")
        else:
            logger.warning(
                f"CSV file not found at {CSV_PATH}. Please upload CSV file! Proceeding with topology query"
            )
        abnormal_host = []
        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "string",
                "data": [],
            }
            node_id = node_ids.get(o.host)
            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                    sync_check_node=self.sync_check_node,
                )
                continue
            stdout = list(o.stdout)
            if not stdout:
                abnormal_host.append(o.host)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} no topology info",
                    sync_check_node=self.sync_check_node,
                )
                continue
            extractor = ExtractData(stdout)
            process_data = extractor.process_data
            detail_result.extend(process_data)
            stderr = list(o.stderr)
            detail_result.extend(stderr)
            stdout_data = extractor.extract_data()
            formatted_output = self.format_topology_data(stdout_data)
            detail_result.append(f"{o.host} GPU topology:")
            detail_result.extend(formatted_output)
            format_result["data"].append(f"{o.host} GPU topology:")
            format_result["data"].extend(formatted_output)
            abnormal_results = []
            if csv_exists and csv_data:
                detail_result.append(
                    f"Found CSV file at {CSV_PATH}. Proceeding with topology comparison."
                )
                judge_gpu_nic_output = self.judge_gpu_nic_consistent(
                    stdout_data, csv_data)
                for differ_item, differ_detail in judge_gpu_nic_output.items():
                    if differ_detail:
                        msg = self.show_info[differ_item].format(
                            ",".join(differ_detail))
                        error_info_lines = [
                            line for line in msg.split("\n") if line]
                        abnormal_results.extend(error_info_lines)

                judge_relation_output = self.judge_relation_consistent(
                    stdout_data, csv_data)
                if judge_relation_output:
                    abnormal_results.append(
                        "-----GPU-NIC relationship not consistent-----")
                    abnormal_results.extend(judge_relation_output)
            else:
                no_csv_msg = f"CSV file not found at {CSV_PATH} or data is empty. Please upload CSV file! Proceeding with topology query"
                detail_result.append(no_csv_msg)
                format_result["data"].append(no_csv_msg)
            status = TaskStatus.FAILED.value
            if not abnormal_results and csv_exists and csv_data:
                status = TaskStatus.SUCCESS.value
            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)
            detail_result.append(o.host + " exec " + status)
            detail_result.extend(abnormal_results)
            format_result["data"].append(o.host + " exec " + status)
            format_result["data"].extend(abnormal_results)
            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
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

    def format_topology_data(self, topology_data):
        formatted_lines = []

        # 获取所有 GPU ID 和 NIC
        gpu_ids = sorted(topology_data.keys(), key=natural_sort_key)
        nics = sorted(topology_data[gpu_ids[0]].keys(), key=natural_sort_key)

        if not gpu_ids:
            logger.error("No GPU IDs found for formatting")
            return ["No GPU IDs found in topology data"]
        if not nics:
            logger.error("No NICs found for formatting")
            return ["No NICs found in topology data"]

        # 计算每列的宽度
        header_width = max(len(gpu) for gpu in gpu_ids) + 2  # GPU 列宽度
        nic_width = max(len(nic) for nic in nics) + 2  # NIC 列宽度

        # 生成表头（relation + GPU IDs）
        header_format = "{:<{nic_w}}\t" + \
            "\t".join(["{:<{gpu_w}}" for _ in gpu_ids])
        header = header_format.format(
            "relation", *gpu_ids, nic_w=nic_width, gpu_w=header_width)
        formatted_lines.append(header)

        # 生成表格数据
        row_format = "{:<{nic_w}}\t" + \
            "\t".join(["{:<{gpu_w}}" for _ in gpu_ids])
        for nic in nics:
            line = row_format.format(
                nic,
                *[topology_data[gpu][nic] for gpu in gpu_ids],
                nic_w=nic_width,
                gpu_w=header_width,
            )
            formatted_lines.append(line)

        return formatted_lines
