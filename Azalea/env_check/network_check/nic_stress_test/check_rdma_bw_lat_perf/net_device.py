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

from pssh.config import HostConfig
from pssh.output import HostOutput

try:
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime

except Exception:
    import sys

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(parent_dir)
    from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime


logger = logging.getLogger(__name__)


class NetDev:
    def __init__(self):
        self.ibdev2netdev = {}
        self.netdev2ibdev = {}
        self.netdev2numa = {}
        self.netdev_ips = {}

    def get_ibdev2netdev(self, nodes, exec_timeout):
        self.ibdev2netdev = {}
        self.netdev2ibdev = {}
        host_ips = []
        host_configs = []
        is_error = False
        cmd = """
        rdma link | grep netdev | awk '{split($2,a,"/"); print a[1]","$NF}'
        """
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
            timeout=exec_timeout,
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
            net_devs = {}
            ib_devs = {}
            for line in stdout:
                nics = line.split(",")
                if len(nics) != 2:
                    logger.warn(f"{o.host} ibdev2netdev wrong format: {line}")
                    continue
                net_devs[nics[0].strip()] = nics[1].strip()
                ib_devs[nics[1].strip()] = nics[0].strip()
            logger.info(f"Get host {o.host} ibdev2netdev: {net_devs}")
            self.ibdev2netdev[o.host] = net_devs
            self.netdev2ibdev[o.host] = ib_devs
        if is_error:
            raise Exception("Get all ibdev2netdev errors")
        logger.info("Get all ibdev2netdev in hosts completed.")

    def get_netdev2numa(self, nodes, exec_timeout):
        self.netdev2numa = {}
        bash_script = """
        netdevs=$(rdma link | grep netdev | awk '{print $NF}')
        for netdev in $netdevs; do
            numa_node_path="/sys/class/net/$netdev/device/numa_node"
            if [ -f "$numa_node_path" ]; then
                numa_node=$(cat "$numa_node_path")
                echo "$netdev,$numa_node"
            fi
        done
        """
        cmd = bash_script
        host_ips = []
        host_configs = []
        is_error = False
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
            timeout=exec_timeout,
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
            net_numas = {}
            for line in stdout:
                if line == "None":
                    continue
                nics = line.split(",")
                if len(nics) != 2:
                    logger.warn(
                        f"{o.host} netdev numa node wrong format: {line}")
                    continue
                net_numas[nics[0].strip()] = nics[1].strip()
            logger.info(f"Get host {o.host} netdev numa node: {net_numas}")
            self.netdev2numa[o.host] = net_numas
        if is_error:
            raise Exception("Get all netdev numa node errors")
        logger.info("Get all netdev numa node in hosts completed.")

    def get_netdev_ips(self, nodes, exec_timeout):
        self.netdev_ips = {}
        bash_script = """
        netdevs=$(rdma link | grep netdev | awk '{print $NF}')
        for netdev in $netdevs; do
            ip_addr_info=`ip addr show $netdev 2>/dev/null`
            nic_addr=`echo "$ip_addr_info" |grep -w "inet" |head -n 1 |awk '{print $2}' |awk -F '/' '{print $1}'`
            if [[ -z $nic_addr ]]; then
                nic_addr=`echo "$ip_addr_info" |grep -w "inet6" | grep -Ev "[[:space:]]fe80" |head -n 1 |awk '{print $2}' |awk -F '/' '{print $1}'`
            fi
            echo "$netdev,$nic_addr"
        done
        """
        cmd = bash_script
        host_ips = []
        host_configs = []
        is_error = False
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
            timeout=exec_timeout,
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
            net_ips = {}
            for line in stdout:
                if line == "None":
                    continue
                nics = line.split(",")
                if len(nics) != 2:
                    logger.warn(
                        f"{o.host} netdev ip addr wrong format: {line}")
                    continue
                net_ips[nics[0].strip()] = nics[1].strip()
            logger.info(f"Get host {o.host} netdev ip addrs: {net_ips}")
            self.netdev_ips[o.host] = net_ips
        if is_error:
            raise Exception("Get all netdev ip addr errors")
        logger.info("Get all netdev ip addr in hosts completed.")

    def get_ibdev_numa(self, node, ibdev):
        net_devs = self.ibdev2netdev.get(node.ip_address, {})
        net_dev = net_devs.get(ibdev, "")
        if net_dev == "":
            return ""
        numas = self.netdev2numa.get(node.ip_address, {})
        numa = numas.get(net_dev, "")
        return numa

    def get_ibdev_by_netdev(self, node, netdev):
        ib_devs = self.netdev2ibdev.get(node.ip_address, {})
        ib_dev = ib_devs.get(netdev, "")
        return ib_dev

    def get_netdev_numa(self, node, netdev):
        numas = self.netdev2numa.get(node.ip_address, {})
        numa = numas.get(netdev, "")
        return numa

    def get_netdev_ipaddr(self, node, netdev):
        ips = self.netdev_ips.get(node.ip_address, {})
        ipaddr = ips.get(netdev, "")
        return ipaddr
