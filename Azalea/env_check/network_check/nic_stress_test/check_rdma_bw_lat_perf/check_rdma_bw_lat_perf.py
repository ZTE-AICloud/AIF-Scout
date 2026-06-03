# -*- coding: utf-8 -*-
#
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
from typing import List
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pssh.config import HostConfig
from pssh.output import HostOutput
from pssh.clients.native import SSHClient as NativeSSHClient

try:
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from env_check.network_check.nic_stress_test.check_rdma_bw_lat_perf import process_bw
    from env_check.network_check.nic_stress_test.check_rdma_bw_lat_perf import net_device

    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime, execute_commands_on_host
    from utils.consts import TaskStatus


except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(parent_dir)
    from env_check.base import Task
    from env_check.base import TaskMetadata
    from env_check.network_check.nic_stress_test.check_rdma_bw_lat_perf import process_bw
    from env_check.network_check.nic_stress_test.check_rdma_bw_lat_perf import net_device

    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime, execute_commands_on_host
    from utils.consts import TaskStatus


logger = logging.getLogger(__name__)

RDMA_PERF_DIR = "/app/pv/perf/rdma"

IB_BW_CMDS = ["ib_write_bw", "ib_send_bw", "ib_read_bw"]
IB_LAT_CMDS = ["ib_write_lat", "ib_send_lat", "ib_read_lat"]


class CheckRdmaBwLatPerfTask(Task):
    metadata = TaskMetadata(
        check_item="rdma_bw_lat_perf_check",
    )

    @staticmethod
    def validate(request: dict):
        """validate task request.

        Args:
            request (dict): request data
        """
        nodes = request.get("nodes")
        if nodes is None or len(nodes) < 2:
            raise ValueError("Please select at least two nodes.")

    def execute(self) -> None:
        self.start_time = datetime.now()
        self.host_listen_ports = {}
        self.netdev = net_device.NetDev()
        self.detail_result = []
        self.stopped = False

        if len(self.task_options.nodes) < 2:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, "Please select at least two nodes."
            )
            logger.error("Please select at least two nodes.")
            return
        try:
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value,
                "Start exec check RDMA bandwith and latency performance...",
            )
            logger.info(
                f"Start exec check RDMA bandwith and latency performance, receive parameters {self.task_options.task_params}"
            )
            mode = self.task_options.task_params.get("mode")
            opr_cmd = self.task_options.task_params.get("opr_cmd")
            network_devices = self.task_options.task_params.get(
                "param_nic", "")
            server_node_ips = self.task_options.task_params.get("server_nodes")
            server_nics = self.task_options.task_params.get("server_nics")
            qps = self.task_options.task_params.get("qps", "")
            sizes = self.task_options.task_params.get("sizes", "")
            duration = self.task_options.task_params.get("duration")
            gid = self.task_options.task_params.get("gid_index")
            rdma_cm = self.task_options.task_params.get("rdma_cm")
            post_list = self.task_options.task_params.get("post_list")
            tx_depth = self.task_options.task_params.get("tx_depth")
            rx_depth = self.task_options.task_params.get("rx_depth")
            timeout = self.task_options.task_params.get("timeout")
            iterations = self.task_options.task_params.get("iterations")

            supported_modes = ["n2n", "fullmesh", "all_n2n", "all_fullmesh"]
            if mode not in supported_modes:
                raise Exception(f"mode should be in {supported_modes}")
            if mode == "fullmesh" and (not server_node_ips or not server_nics):
                raise Exception(
                    "Please input server node ip address and server nics!")
            if mode == "n2n" and not server_node_ips:
                raise Exception("Please input server node ip address!")
            supported_cmds = IB_BW_CMDS + IB_LAT_CMDS
            if opr_cmd not in supported_cmds:
                raise Exception(f"command should be in {supported_cmds}")
            network_devices = [
                network_device.strip() for network_device in network_devices.split(",")
            ]
            qps = [qp.strip() for qp in qps.split(",")]
            sizes = [size.strip() for size in sizes.split(",")]

            if rdma_cm:
                if rdma_cm not in ["True", "False", "true", "false"]:
                    raise Exception(f"rdma_cm:{rdma_cm} params is invalid!")
                rdma_cm = rdma_cm.lower()
            is_rdma_cm = True if rdma_cm == "true" else False

            self.stop_all_opr(opr_cmd)
            self.detail_result.append(
                f"All run stop {opr_cmd} in hosts completed.")
            self.async_create_remote_dir(self.PSSH_EXEC_TIMEOUT)
            self.netdev.get_ibdev2netdev(
                self.task_options.nodes, self.PSSH_EXEC_TIMEOUT)
            self.netdev.get_netdev2numa(
                self.task_options.nodes, self.PSSH_EXEC_TIMEOUT)
            self.netdev.get_netdev_ips(
                self.task_options.nodes, self.PSSH_EXEC_TIMEOUT)
            if mode == "fullmesh":
                self.fullmesh(
                    opr_cmd,
                    network_devices,
                    server_node_ips,
                    server_nics,
                    qps,
                    sizes,
                    duration,
                    gid,
                    is_rdma_cm,
                    post_list,
                    tx_depth,
                    rx_depth,
                    timeout,
                    iterations,
                )
            elif mode == "all_fullmesh":
                self.all_fullmesh(
                    opr_cmd,
                    network_devices,
                    qps,
                    sizes,
                    duration,
                    gid,
                    is_rdma_cm,
                    post_list,
                    tx_depth,
                    rx_depth,
                    timeout,
                    iterations,
                )
            elif mode == "all_n2n":
                self.all_n2n(
                    opr_cmd,
                    network_devices,
                    qps,
                    sizes,
                    duration,
                    gid,
                    is_rdma_cm,
                    post_list,
                    tx_depth,
                    rx_depth,
                    timeout,
                    iterations,
                )
            else:
                self.n2n(
                    opr_cmd,
                    network_devices,
                    server_node_ips,
                    qps,
                    sizes,
                    duration,
                    gid,
                    is_rdma_cm,
                    post_list,
                    tx_depth,
                    rx_depth,
                    timeout,
                    iterations,
                )
            if self.stopped:
                logger.info("Task is stopped, not wait to handle result")
                return
            time.sleep(10)
            if self.stopped:
                logger.info("Task is stopped, not handing result")
                return
            self.async_copy_from_remote()
            self.recursive_export_csv(opr_cmd)

            format_result = {
                "result_type": "string",
                "data": [f"Please view result details in {self.get_local_perf_path()}"],
            }
            self.detail_result.append(
                f"Please view result details in {self.get_local_perf_path()}")
            node_ids = [node.node_id for node in self.task_options.nodes]
            status = TaskStatus.SUCCESS.value if not self.stopped else TaskStatus.STOPPED.value
            msg = "" if not self.stopped else "Stopped by user"
            self.save_check_result_progress(
                node_ids,
                status,
                msg,
                self.detail_result,
                [format_result],
            )
            self.save_check_item_progress(status, msg)
        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}")
            logger.error(
                f"Check RDMA bandwith and latency performance exception: {e}")
        finally:
            self.stop_all_opr(opr_cmd)
            self.async_rm_remote_dir(self.PSSH_EXEC_TIMEOUT)

    def stop(self):
        logger.info("Stop check.")
        self.stopped = True
        # release source by finally code block in execute()
        # Otherwise, should release source here.

    def get_remote_node_perf_path(self, node) -> str:
        dir_name = self.get_node_perf_dir_name(node)
        return f"/home/{node.username}/azalea/perf/rdma/{dir_name}"

    def get_node_perf_dir_name(self, node) -> str:
        fmt_start = self.start_time.strftime("%Y_%m_%d_%H_%M_%S")
        dir_name = node.node_name + "_" + node.ip_address + "_" + fmt_start
        return dir_name

    def get_local_perf_path(self) -> str:
        fmt_start = self.start_time.strftime("%Y_%m_%d_%H_%M_%S")
        return f"{RDMA_PERF_DIR}/{self.env_check_item.task.task_name}/{fmt_start}"

    def n2n(
        self,
        opr_cmd,
        network_devices,
        server_node_ips,
        qps,
        sizes,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        timeout,
        iterations,
    ):
        if not server_node_ips:
            raise Exception("Please input server node ip address!")
        server_node_ips = [ip.strip() for ip in server_node_ips.split(",")]
        pssh_exec_timeout = self.PSSH_EXEC_TIMEOUT * 2
        if timeout is not None and timeout > 0:
            pssh_exec_timeout = timeout
        elif duration is not None and duration > 0:
            pssh_exec_timeout = duration * 2 + self.PSSH_EXEC_TIMEOUT
        nodes = self.task_options.nodes
        other_same_nic_counts = len(nodes) - 1
        cmd_index = 0
        for qp in qps:
            if self.stopped:
                return
            for size in sizes:
                if self.stopped:
                    return
                self.get_all_listen_ports()
                client_node_cmds = {}
                client_node_pre_cmds = {}
                server_node_cmds = {}
                for server_node in nodes:
                    if self.stopped:
                        return
                    if server_node.ip_address not in server_node_ips:
                        continue
                    start_port = 18515
                    server_nic_ports = {}
                    listened_ports = self.host_listen_ports.get(
                        server_node.ip_address, [])
                    server_network_devices = network_devices
                    for nic in server_network_devices:
                        if self.stopped:
                            return
                        available_ports = get_available_ports(
                            start_port, listened_ports, other_same_nic_counts
                        )
                        if len(available_ports) != other_same_nic_counts:
                            logger.error(
                                f"Get {server_node.ip_address} {nic} available ports:{available_ports}, not equal {other_same_nic_counts}"
                            )
                            raise Exception(
                                f"Get {server_node.ip_address} {nic} available ports exception"
                            )
                        server_nic_ports[nic] = available_ports
                        start_port = available_ports[len(
                            available_ports) - 1] + 1
                    logger.info(
                        f"n2n: {server_node.ip_address} node will be listen ports: {server_nic_ports}"
                    )
                    nic_ports = server_nic_ports
                    server_cmds = self.build_server_cmds(
                        opr_cmd,
                        qp,
                        size,
                        duration,
                        gid,
                        is_rdma_cm,
                        post_list,
                        tx_depth,
                        rx_depth,
                        server_node,
                        nic_ports,
                        pssh_exec_timeout,
                        iterations,
                    )
                    server_node_cmds[server_node.ip_address] = server_cmds
                    index = 0
                    for client_node in nodes:
                        if self.stopped:
                            return
                        if client_node.ip_address == server_node.ip_address:
                            continue
                        cmds = []
                        pre_cmds = []
                        client_network_devices = network_devices
                        for client_nic in client_network_devices:
                            if self.stopped:
                                return
                            server_ports = server_nic_ports.get(client_nic)
                            server_port = server_ports[index]
                            server_nic = client_nic
                            pre_cmd, cmd = self.build_pre_and_client_cmd(
                                client_node,
                                cmd_index,
                                opr_cmd,
                                client_nic,
                                server_port,
                                qp,
                                size,
                                duration,
                                gid,
                                is_rdma_cm,
                                post_list,
                                tx_depth,
                                rx_depth,
                                server_node,
                                server_nic,
                                pssh_exec_timeout,
                                iterations,
                            )
                            pre_cmds.append(pre_cmd)
                            cmds.append(cmd)
                            cmd_index = cmd_index + 1
                        index = index + 1
                        client_pre_cmds = client_node_pre_cmds.get(
                            client_node.ip_address, [])
                        client_pre_cmds.extend(pre_cmds)
                        client_node_pre_cmds[client_node.ip_address] = client_pre_cmds
                        client_cmds = client_node_cmds.get(
                            client_node.ip_address, [])
                        client_cmds.extend(cmds)
                        client_node_cmds[client_node.ip_address] = client_cmds
                self.start_client_commands(
                    "pre", client_node_pre_cmds, pssh_exec_timeout)
                self.start_server(opr_cmd, server_node_cmds, pssh_exec_timeout)
                # wait server
                if self.stopped:
                    return
                time.sleep(5)
                self.start_client_commands(
                    opr_cmd, client_node_cmds, pssh_exec_timeout)
                # wait client
                self.wait_client(duration, timeout)
                # wait release the task resource
                if self.stopped:
                    return
                time.sleep(10)

    def all_n2n(
        self,
        opr_cmd,
        network_devices,
        qps,
        sizes,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        timeout,
        iterations,
    ):
        pssh_exec_timeout = self.PSSH_EXEC_TIMEOUT * 2
        if timeout is not None and timeout > 0:
            pssh_exec_timeout = timeout
        elif duration is not None and duration > 0:
            pssh_exec_timeout = duration * 2 + self.PSSH_EXEC_TIMEOUT
        nodes = self.task_options.nodes
        other_same_nic_counts = len(nodes) - 1
        cmd_index = 0
        for qp in qps:
            if self.stopped:
                return
            for size in sizes:
                if self.stopped:
                    return
                self.get_all_listen_ports()
                client_node_cmds = {}
                client_node_pre_cmds = {}
                server_node_cmds = {}
                for server_node in nodes:
                    if self.stopped:
                        return
                    start_port = 18515
                    server_nic_ports = {}
                    listened_ports = self.host_listen_ports.get(
                        server_node.ip_address, [])
                    server_network_devices = network_devices
                    for nic in server_network_devices:
                        if self.stopped:
                            return
                        available_ports = get_available_ports(
                            start_port, listened_ports, other_same_nic_counts
                        )
                        if len(available_ports) != other_same_nic_counts:
                            logger.error(
                                f"Get {server_node.ip_address} {nic} available ports:{available_ports}, not equal {other_same_nic_counts}"
                            )
                            raise Exception(
                                f"Get {server_node.ip_address} {nic} available ports exception"
                            )
                        server_nic_ports[nic] = available_ports
                        start_port = available_ports[len(
                            available_ports) - 1] + 1
                    logger.info(
                        f"n2n: {server_node.ip_address} node will be listen ports: {server_nic_ports}"
                    )
                    nic_ports = server_nic_ports
                    server_cmds = self.build_server_cmds(
                        opr_cmd,
                        qp,
                        size,
                        duration,
                        gid,
                        is_rdma_cm,
                        post_list,
                        tx_depth,
                        rx_depth,
                        server_node,
                        nic_ports,
                        pssh_exec_timeout,
                        iterations,
                    )
                    server_node_cmds[server_node.ip_address] = server_cmds
                    index = 0
                    for client_node in nodes:
                        if self.stopped:
                            return
                        if client_node.ip_address == server_node.ip_address:
                            continue
                        cmds = []
                        pre_cmds = []
                        client_network_devices = network_devices
                        for client_nic in client_network_devices:
                            if self.stopped:
                                return
                            server_ports = server_nic_ports.get(client_nic)
                            server_port = server_ports[index]
                            server_nic = client_nic
                            pre_cmd, cmd = self.build_pre_and_client_cmd(
                                client_node,
                                cmd_index,
                                opr_cmd,
                                client_nic,
                                server_port,
                                qp,
                                size,
                                duration,
                                gid,
                                is_rdma_cm,
                                post_list,
                                tx_depth,
                                rx_depth,
                                server_node,
                                server_nic,
                                pssh_exec_timeout,
                                iterations,
                            )
                            pre_cmds.append(pre_cmd)
                            cmds.append(cmd)
                            cmd_index = cmd_index + 1
                        index = index + 1
                        client_pre_cmds = client_node_pre_cmds.get(
                            client_node.ip_address, [])
                        client_pre_cmds.extend(pre_cmds)
                        client_node_pre_cmds[client_node.ip_address] = client_pre_cmds
                        client_cmds = client_node_cmds.get(
                            client_node.ip_address, [])
                        client_cmds.extend(cmds)
                        client_node_cmds[client_node.ip_address] = client_cmds
                self.start_client_commands(
                    "pre", client_node_pre_cmds, pssh_exec_timeout)
                self.start_server(opr_cmd, server_node_cmds, pssh_exec_timeout)
                # wait server
                if self.stopped:
                    return
                time.sleep(5)
                self.start_client_commands(
                    opr_cmd, client_node_cmds, pssh_exec_timeout)
                # wait client
                self.wait_client(duration, timeout)
                # wait release the task resource
                if self.stopped:
                    return
                time.sleep(10)

    def fullmesh(
        self,
        opr_cmd,
        network_devices,
        server_node_ips,
        server_nics,
        qps,
        sizes,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        timeout,
        iterations,
    ):
        if not server_node_ips or not server_nics:
            raise Exception(
                "Please input server node ip address and server nics!")
        server_node_ips = [ip.strip() for ip in server_node_ips.split(",")]
        server_nics = [nic.strip() for nic in server_nics.split(",")]
        pssh_exec_timeout = self.PSSH_EXEC_TIMEOUT * 2
        if timeout is not None and timeout > 0:
            pssh_exec_timeout = timeout
        elif duration is not None and duration > 0:
            pssh_exec_timeout = duration * 2 + self.PSSH_EXEC_TIMEOUT
        nodes = self.task_options.nodes
        other_all_nics_counts = (len(nodes) - 1) * len(network_devices)
        cmd_index = 0
        for qp in qps:
            if self.stopped:
                return
            for size in sizes:
                if self.stopped:
                    return
                self.get_all_listen_ports()
                client_node_cmds = {}
                client_node_pre_cmds = {}
                server_node_cmds = {}
                for server_node in nodes:
                    if self.stopped:
                        return
                    if server_node.ip_address not in server_node_ips:
                        continue
                    start_port = 18515
                    server_nic_ports = {}
                    listened_ports = self.host_listen_ports.get(
                        server_node.ip_address, [])
                    for nic in network_devices:
                        if self.stopped:
                            return
                        if nic not in server_nics:
                            continue
                        available_ports = get_available_ports(
                            start_port, listened_ports, other_all_nics_counts
                        )
                        if len(available_ports) != other_all_nics_counts:
                            logger.error(
                                f"Get {server_node.ip_address} {nic} available ports:{available_ports}, not equal {other_all_nics_counts}"
                            )
                            raise Exception(
                                f"Get {server_node.ip_address} {nic} available ports exception"
                            )
                        server_nic_ports[nic] = available_ports
                        start_port = available_ports[len(
                            available_ports) - 1] + 1
                    logger.info(
                        f"fullmesh: {server_node.ip_address} node will be listen ports: {server_nic_ports}"
                    )
                    server_cmds = self.build_server_cmds(
                        opr_cmd,
                        qp,
                        size,
                        duration,
                        gid,
                        is_rdma_cm,
                        post_list,
                        tx_depth,
                        rx_depth,
                        server_node,
                        server_nic_ports,
                        pssh_exec_timeout,
                        iterations,
                    )
                    server_node_cmds[server_node.ip_address] = server_cmds
                    for server_nic in network_devices:
                        if self.stopped:
                            return
                        if server_nic not in server_nics:
                            continue
                        index = 0
                        for client_node in nodes:
                            if self.stopped:
                                return
                            if client_node.ip_address == server_node.ip_address:
                                continue
                            cmds = []
                            pre_cmds = []
                            for client_nic in network_devices:
                                if self.stopped:
                                    return
                                server_ports = server_nic_ports.get(server_nic)
                                server_port = server_ports[index]
                                pre_cmd, cmd = self.build_pre_and_client_cmd(
                                    client_node,
                                    cmd_index,
                                    opr_cmd,
                                    client_nic,
                                    server_port,
                                    qp,
                                    size,
                                    duration,
                                    gid,
                                    is_rdma_cm,
                                    post_list,
                                    tx_depth,
                                    rx_depth,
                                    server_node,
                                    server_nic,
                                    pssh_exec_timeout,
                                    iterations,
                                )
                                pre_cmds.append(pre_cmd)
                                cmds.append(cmd)
                                cmd_index = cmd_index + 1
                                index = index + 1
                            client_pre_cmds = client_node_pre_cmds.get(
                                client_node.ip_address, [])
                            client_pre_cmds.extend(pre_cmds)
                            client_node_pre_cmds[client_node.ip_address] = client_pre_cmds
                            client_cmds = client_node_cmds.get(
                                client_node.ip_address, [])
                            client_cmds.extend(cmds)
                            client_node_cmds[client_node.ip_address] = client_cmds
                self.start_client_commands(
                    "pre", client_node_pre_cmds, pssh_exec_timeout)
                self.start_server(opr_cmd, server_node_cmds, pssh_exec_timeout)
                # wait server
                if self.stopped:
                    return
                time.sleep(5)
                self.start_client_commands(
                    opr_cmd, client_node_cmds, pssh_exec_timeout)
                # wait client
                self.wait_client(duration, timeout)
                # wait release the task resource
                if self.stopped:
                    return
                time.sleep(10)

    def all_fullmesh(
        self,
        opr_cmd,
        network_devices,
        qps,
        sizes,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        timeout,
        iterations,
    ):
        pssh_exec_timeout = self.PSSH_EXEC_TIMEOUT * 2
        if timeout is not None and timeout > 0:
            pssh_exec_timeout = timeout
        elif duration is not None and duration > 0:
            pssh_exec_timeout = duration * 2 + self.PSSH_EXEC_TIMEOUT
        nodes = self.task_options.nodes
        other_all_nics_counts = (len(nodes) - 1) * len(network_devices)
        cmd_index = 0
        for qp in qps:
            if self.stopped:
                return
            for size in sizes:
                if self.stopped:
                    return
                self.get_all_listen_ports()
                client_node_cmds = {}
                client_node_pre_cmds = {}
                server_node_cmds = {}
                for server_node in nodes:
                    if self.stopped:
                        return
                    start_port = 18515
                    server_nic_ports = {}
                    listened_ports = self.host_listen_ports.get(
                        server_node.ip_address, [])
                    for nic in network_devices:
                        if self.stopped:
                            return
                        available_ports = get_available_ports(
                            start_port, listened_ports, other_all_nics_counts
                        )
                        if len(available_ports) != other_all_nics_counts:
                            logger.error(
                                f"Get {server_node.ip_address} {nic} available ports:{available_ports}, not equal {other_all_nics_counts}"
                            )
                            raise Exception(
                                f"Get {server_node.ip_address} {nic} available ports exception"
                            )
                        server_nic_ports[nic] = available_ports
                        start_port = available_ports[len(
                            available_ports) - 1] + 1
                    logger.info(
                        f"fullmesh: {server_node.ip_address} node will be listen ports: {server_nic_ports}"
                    )
                    server_cmds = self.build_server_cmds(
                        opr_cmd,
                        qp,
                        size,
                        duration,
                        gid,
                        is_rdma_cm,
                        post_list,
                        tx_depth,
                        rx_depth,
                        server_node,
                        server_nic_ports,
                        pssh_exec_timeout,
                        iterations,
                    )
                    server_node_cmds[server_node.ip_address] = server_cmds
                    for server_nic in network_devices:
                        if self.stopped:
                            return
                        index = 0
                        for client_node in nodes:
                            if self.stopped:
                                return
                            if client_node.ip_address == server_node.ip_address:
                                continue
                            cmds = []
                            pre_cmds = []
                            for client_nic in network_devices:
                                if self.stopped:
                                    return
                                server_ports = server_nic_ports.get(server_nic)
                                server_port = server_ports[index]
                                pre_cmd, cmd = self.build_pre_and_client_cmd(
                                    client_node,
                                    cmd_index,
                                    opr_cmd,
                                    client_nic,
                                    server_port,
                                    qp,
                                    size,
                                    duration,
                                    gid,
                                    is_rdma_cm,
                                    post_list,
                                    tx_depth,
                                    rx_depth,
                                    server_node,
                                    server_nic,
                                    pssh_exec_timeout,
                                    iterations,
                                )
                                pre_cmds.append(pre_cmd)
                                cmds.append(cmd)
                                cmd_index = cmd_index + 1
                                index = index + 1
                            client_pre_cmds = client_node_pre_cmds.get(
                                client_node.ip_address, [])
                            client_pre_cmds.extend(pre_cmds)
                            client_node_pre_cmds[client_node.ip_address] = client_pre_cmds
                            client_cmds = client_node_cmds.get(
                                client_node.ip_address, [])
                            client_cmds.extend(cmds)
                            client_node_cmds[client_node.ip_address] = client_cmds
                self.start_client_commands(
                    "pre", client_node_pre_cmds, pssh_exec_timeout)
                self.start_server(opr_cmd, server_node_cmds, pssh_exec_timeout)
                # wait server
                if self.stopped:
                    return
                time.sleep(5)
                self.start_client_commands(
                    opr_cmd, client_node_cmds, pssh_exec_timeout)
                # wait client
                self.wait_client(duration, timeout)
                # wait release the task resource
                if self.stopped:
                    return
                time.sleep(10)

    def build_common_cmd(
        self,
        opr_cmd,
        nic,
        port,
        qp,
        size,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        iterations,
    ):
        cmd = f"{opr_cmd} -d {nic} -p {port}"
        if qp and opr_cmd not in IB_LAT_CMDS:
            # Multiple QPs only available on bw tests
            cmd = f"{cmd} -q {qp}"
        if size:
            if size == "0":
                cmd = f"{cmd} -a"
            else:
                cmd = f"{cmd} -s {size}"
        if duration is not None and duration > 0 and size != "0":
            # Duration mode currently doesn't support running on
            #  '-a' all sizes.
            cmd = f"{cmd} -D {duration}"
        if gid is not None:
            cmd = f"{cmd} -x {gid}"
        if is_rdma_cm:
            cmd = f"{cmd} -R"
        if post_list is not None:
            cmd = f"{cmd} -l {post_list}"
        if tx_depth is not None:
            cmd = f"{cmd} -t {tx_depth}"
        if rx_depth is not None:
            cmd = f"{cmd} -r {rx_depth}"
        if opr_cmd not in IB_LAT_CMDS:
            cmd = f"{cmd} --report_gbits"
        if iterations is not None:
            cmd = f"{cmd} -n {iterations}"
        cmd = f"{cmd} -F --cpu_util"
        return cmd

    def build_pre_and_client_cmd(
        self,
        node,
        index,
        opr_cmd,
        nic,
        port,
        qp,
        size,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        server_node,
        server_nic,
        exec_timeout,
        iterations,
    ):
        remote_path = self.get_remote_node_perf_path(node)
        remote_file = (
            f"{remote_path}/{opr_cmd}_{nic}_{server_node.ip_address}_{server_nic}_{index}.perf"
        )
        ibdev = self.netdev.get_ibdev_by_netdev(node, nic)
        cmd = self.build_common_cmd(
            opr_cmd,
            ibdev,
            port,
            qp,
            size,
            duration,
            gid,
            is_rdma_cm,
            post_list,
            tx_depth,
            rx_depth,
            iterations,
        )
        numa = self.netdev.get_netdev_numa(node, nic)
        if numa != "":
            cmd = f"numactl --cpubind={numa} {cmd}"
        server_nic_addr = self.netdev.get_netdev_ipaddr(
            server_node, server_nic)
        if not server_nic_addr:
            server_nic_addr = server_node.ip_address
        cmd = f"{cmd} {server_nic_addr}"
        pre_cmd = (
            "Client Host: %s(%s) Client Device: %s\n"
            "Server Host: %s(%s) Server Device: %s\n"
            "QP: %s Size: %s\n"
            "Command: %s\n"
            "Test Output:\n"
        ) % (
            node.node_name,
            node.ip_address,
            nic,
            server_node.node_name,
            server_node.ip_address,
            server_nic,
            qp,
            size,
            cmd,
        )
        pre_cmd = f'echo -e "{pre_cmd}" > {remote_file} 2>&1'
        if exec_timeout > 0:
            cmd = f"timeout {exec_timeout} {cmd}"
        cmd = f"nohup {cmd} >> {remote_file} 2>&1 &"
        return pre_cmd, cmd

    def build_server_cmds(
        self,
        opr_cmd,
        qp,
        size,
        duration,
        gid,
        is_rdma_cm,
        post_list,
        tx_depth,
        rx_depth,
        server_node,
        nic_ports,
        exec_timeout,
        iterations,
    ):
        cmds = []
        for nic, ports in nic_ports.items():
            ibdev = self.netdev.get_ibdev_by_netdev(server_node, nic)
            for port in ports:
                cmd = self.build_common_cmd(
                    opr_cmd,
                    ibdev,
                    port,
                    qp,
                    size,
                    duration,
                    gid,
                    is_rdma_cm,
                    post_list,
                    tx_depth,
                    rx_depth,
                    iterations,
                )
                numa = self.netdev.get_netdev_numa(server_node, nic)
                if numa != "":
                    cmd = f"numactl --cpubind={numa} {cmd}"
                if exec_timeout > 0:
                    cmd = f"timeout {exec_timeout} {cmd}"
                cmd = f"nohup {cmd} &> /dev/null &"
                cmds.append(cmd)
        return cmds

    def start_server(self, opr_cmd, server_cmds, exec_timeout):
        if self.stopped:
            return
        logger.info(f"Start {opr_cmd} server")
        self.detail_result.append(f"Start {opr_cmd} server")
        logger.debug(f"Run {opr_cmd} server commands:{server_cmds}")
        self.async_run_diff_commands_on_hosts(server_cmds, exec_timeout)

    def start_client_commands(self, opr_cmd, host_cmds: dict, exec_timeout):
        if self.stopped:
            return
        logger.info(f"Start {opr_cmd} client")
        self.detail_result.append(f"Start {opr_cmd} client")
        logger.debug(f"Run {opr_cmd} client commands:{host_cmds}")
        self.async_run_diff_commands_on_hosts(host_cmds, exec_timeout)

    def async_run_commands_on_hosts(self, cmds, exec_timeout):
        if self.stopped:
            return
        nodes = self.task_options.nodes
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = [
                executor.submit(
                    execute_commands_on_host,
                    node.ip_address,
                    node.username,
                    node.ssh_password,
                    node.port,
                    cmds,
                    exec_timeout,
                )
                for node in nodes
                if not self.stopped
            ]
            # wait all tasks completed
            for future in as_completed(futures):
                future.result()
        logger.info("All run commands in hosts completed.")
        self.detail_result.append("All run commands in hosts completed.")

    def async_run_diff_commands_on_hosts(self, host_cmds: dict, exec_timeout):
        if self.stopped:
            return
        nodes = self.task_options.nodes
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = []
            for node in nodes:
                if self.stopped:
                    break
                cmds = host_cmds.get(node.ip_address, [])
                futures.append(
                    executor.submit(
                        execute_commands_on_host,
                        node.ip_address,
                        node.username,
                        node.ssh_password,
                        node.port,
                        cmds,
                        exec_timeout,
                    )
                )
            # wait all tasks completed
            for future in as_completed(futures):
                future.result()
        logger.info("All run different commands in hosts completed.")
        self.detail_result.append(
            "All run different commands in hosts completed.")

    def stop_all_opr(self, opr_cmd):
        nodes = self.task_options.nodes
        host_ips = []
        host_configs = []
        is_error = False
        cmd = f"pkill -9 {opr_cmd}"
        for node in nodes:
            host_ips.append(node.ip_address)
            host_configs.append(
                HostConfig(user=node.username, port=node.port,
                           password=node.ssh_password)
            )
        output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
            host_ips,
            host_configs,
            cmd,
            timeout=self.PSSH_EXEC_TIMEOUT,
            stop_on_errors=False,
        )
        for o in output:
            if o.exception:
                is_error = True
                formatted_message = self.format_exception(o.exception)
                logger.error(
                    f"{o.host} {cmd} raise an exception: {formatted_message}")
                continue
            if o.exit_code > 0:
                # maybe 1, cmd not running, not raise exception
                for line in o.stderr:
                    logger.error(
                        f"{o.host} {cmd} exit code: {o.exit_code}, has error: {line.strip()}"
                    )
        if is_error:
            raise Exception(f"{cmd} errors")
        logger.info(f"All run stop {opr_cmd} in hosts completed.")

    def get_all_listen_ports(self):
        nodes = self.task_options.nodes
        self.host_listen_ports = {}
        host_ips = []
        host_configs = []
        is_error = False
        cmd = "ss -lntup | awk '{print $5}' | grep -oE '[0-9]+$' | sort -nu"
        for node in nodes:
            host_ips.append(node.ip_address)
            host_configs.append(
                HostConfig(user=node.username, port=node.port,
                           password=node.ssh_password)
            )
        output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
            host_ips,
            host_configs,
            cmd,
            timeout=self.PSSH_EXEC_TIMEOUT,
            stop_on_errors=False,
        )
        for o in output:
            if o.exception:
                is_error = True
                formatted_message = self.format_exception(o.exception)
                logger.error(
                    f"{o.host} {cmd} raise an exception: {formatted_message}")
                continue
            if o.exit_code > 0:
                for line in o.stderr:
                    logger.error(
                        f"{o.host} {cmd} exit code: {o.exit_code}, has error: {line.strip()}"
                    )
            stdout = list(o.stdout)
            ports = []
            for line in stdout:
                port = line.strip()
                if port.isdigit():
                    ports.append(int(port))
            logger.info(f"Get host {o.host} listen ports: {ports}")
            self.host_listen_ports[o.host] = ports
        if is_error:
            raise Exception("Get all listen ports errors")
        logger.info("Get all listen ports in hosts completed.")

    def async_create_remote_dir(self, exec_timeout):
        if self.stopped:
            return
        logger.info("Begin create remote performance dir")
        nodes = self.task_options.nodes
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = []
            for node in nodes:
                if self.stopped:
                    break
                remote_dir = self.get_remote_node_perf_path(node)
                cmds = [f"mkdir -p {remote_dir}"]
                futures.append(
                    executor.submit(
                        execute_commands_on_host,
                        node.ip_address,
                        node.username,
                        node.ssh_password,
                        node.port,
                        cmds,
                        exec_timeout,
                    )
                )
            # wait all tasks completed
            for future in as_completed(futures):
                future.result()
        logger.info("All create remote dir tasks completed.")

    def async_rm_remote_dir(self, exec_timeout):
        logger.info("Begin rm remote performance dir")
        nodes = self.task_options.nodes
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = []
            for node in nodes:
                remote_dir = self.get_remote_node_perf_path(node)
                cmds = [f"rm -rf {remote_dir}"]
                futures.append(
                    executor.submit(
                        execute_commands_on_host,
                        node.ip_address,
                        node.username,
                        node.ssh_password,
                        node.port,
                        cmds,
                        exec_timeout,
                    )
                )
            # wait all tasks completed
            for future in as_completed(futures):
                future.result()
        logger.info("All rm remote dir tasks completed.")

    def async_copy_from_remote(self):
        if self.stopped:
            return
        logger.info("Begin copy from remote performance dir")
        local_perf_path = self.get_local_perf_path()
        nodes = self.task_options.nodes
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = []
            for node in nodes:
                if self.stopped:
                    break
                remote_path = self.get_remote_node_perf_path(node)
                remote_node_dir = os.path.basename(remote_path)
                local_node_perf_path = f"{local_perf_path}/{remote_node_dir}"
                if not os.path.exists(local_node_perf_path):
                    os.makedirs(local_node_perf_path)
                futures.append(
                    executor.submit(
                        copy_from_remote,
                        node.ip_address,
                        node.username,
                        node.ssh_password,
                        node.port,
                        remote_path,
                        local_node_perf_path,
                    )
                )
            # wait all tasks completed
            for future in as_completed(futures):
                future.result()
        logger.info("All copy files from remote tasks completed.")
        self.detail_result.append(
            "All copy files from remote tasks completed.")

    def wait_client(self, duration, exec_timeout):
        timeout = self.PSSH_EXEC_TIMEOUT
        if exec_timeout is not None and exec_timeout > 0:
            timeout = exec_timeout
        elif duration is not None and duration > 0:
            timeout = duration + 10
        if self.stopped:
            return
        logger.info(f"Wait {timeout} for client")
        time.sleep(timeout)

    def export_csv(self, opr_cmd):
        if self.stopped:
            return
        if opr_cmd not in IB_BW_CMDS:
            return
        logger.info("Begin export csv file")
        local_perf_path = self.get_local_perf_path()
        nodes = self.task_options.nodes
        for node in nodes:
            if self.stopped:
                logger.info("Check stopped, skip export csv")
                return
            remote_path = self.get_remote_node_perf_path(node)
            remote_node_dir = os.path.basename(remote_path)
            local_node_perf_path = f"{local_perf_path}/{remote_node_dir}"
            process_bw.export_csv(local_node_perf_path)
        logger.info("All export csv files completed.")
        self.detail_result.append("All export csv files completed.")

    def recursive_export_csv(self, opr_cmd):
        if self.stopped:
            return
        if opr_cmd not in IB_BW_CMDS:
            return
        logger.info("Begin recursive export csv file")
        local_perf_path = self.get_local_perf_path()
        process_bw.export_csv(local_perf_path, recursive=True)
        logger.info("All recursive export csv files completed.")
        self.detail_result.append("All recursive export csv files completed.")


def copy_from_remote(
    remote_host,
    remote_user,
    remote_password,
    remote_port,
    remote_path,
    local_perf_path,
):
    with NativeSSHClient(
        host=remote_host,
        user=remote_user,
        allow_agent=False,
        password=remote_password,
        port=remote_port,
    ) as client:
        client.copy_remote_file(remote_file=remote_path,
                                local_file=local_perf_path, recurse=True)


def get_available_ports(start_port, listened_ports, counts):
    """
    获取不在已使用端口列表中的指定数量的可用端口。

    :param start_port: 开始查找的端口号
    :param listened_ports: 已经使用的端口列表
    :param counts: 需要获取的可用端口数量
    :return: 包含counts个可用端口的列表
    """
    available_ports = []
    current_port = start_port

    while len(available_ports) < counts:
        if current_port not in listened_ports:
            available_ports.append(current_port)
        current_port += 1

    return available_ports
