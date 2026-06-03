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

import json
import logging
import re

from utils.ssh_tool import HostOutputData, exec_cmd_on_single_host
from utils.ssh_tool import Common_SSH_Exception
from utils.consts import PathConfig

logger = logging.getLogger(__name__)

PSSH_EXEC_TIMEOUT = 30


class NodeInfo:
    def __init__(self, ip_address, username, ssh_password, port=22, initialized=False):
        self.ip_address = ip_address
        self.username = username
        self.ssh_password = ssh_password
        self.port = port
        self.hostname = ""
        self.gpu_manufacturer = ""
        self.gpu_type = ""
        self.gpu_count = 0
        if not initialized:
            self.get_info()

    def execute_cmd(self, cmd: str, log_level="info") -> HostOutputData:
        try:
            log_method = logger.debug if log_level == "debug" else logger.info
            log_method(f"Executing {cmd} on {self.ip_address}")
            output = exec_cmd_on_single_host(
                self.username,
                self.ip_address,
                self.ssh_password,
                cmd,
                port=self.port,
                timeout=PSSH_EXEC_TIMEOUT,
            )
        except Exception as e:
            error_msg = f"Executing {cmd} on {self.ip_address} failed: {e}"
            logger.error(error_msg)
            output = HostOutputData(
                host=self.ip_address, exit_code=-1, std_out=[], std_err=[str(e)]
            )
        return output

    def get_info(self):
        """Fetch both hostname and GPU information."""
        self.get_hostname()
        self.get_gpu_info()

    def get_hostname(self):
        """Fetch the hostname of the node."""
        output = self.execute_cmd("hostname")
        if output.exit_code != 0:
            error_msg = ";".join(output.std_err)
            raise Common_SSH_Exception(error_msg)
        self.hostname = output.std_out[0].strip() if output.std_out else ""
        logger.info(f"hostname of {self.ip_address} is {self.hostname}")

    def get_gpu_info(self):
        """Fetch GPU information from the node."""
        with open(PathConfig.GPU_PCI_JSON, "r") as f:
            gpu_pci_info = json.load(f)
        for gpu_manufacturer, pci_info_list in gpu_pci_info.items():
            for pci_info_dict in pci_info_list:
                vendor_id = pci_info_dict.get("vendor_id", "")
                product_ids = pci_info_dict.get("product_id", {})
                cmd = f"lspci -nnn -d {vendor_id}:"
                output = self.execute_cmd(cmd)
                if output.exit_code != 0 or not output.std_out:
                    continue
                for gpu_type, product_id in product_ids.items():
                    pattern = rf"\[{vendor_id}:{product_id}]"
                    matches = [
                        out for out in output.std_out if re.search(pattern, out)]
                    if len(matches) != 0:
                        self.gpu_manufacturer = gpu_manufacturer
                        self.gpu_type = gpu_type
                        logger.info(
                            f"gpu manufacturer of {self.ip_address} is {self.gpu_manufacturer}")
                        logger.info(
                            f"gpu type of {self.ip_address} is {self.gpu_type}")
                        self.gpu_count = len(matches)
                        break
                    else:
                        continue
                if self.gpu_manufacturer and self.gpu_type:
                    break

            if self.gpu_manufacturer and self.gpu_type:
                break
