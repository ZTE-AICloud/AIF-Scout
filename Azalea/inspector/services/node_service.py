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
import json
import logging
import threading
from typing import List, Dict

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from inspector import models
from system_management.nodes.node_info import NodeInfo
from utils import decryption
from utils.ssh_tool import Common_SSH_Exception
from utils.tools import change_model_item_to_str, is_valid_ip
from inspector.serializers import NodeSerializer
from django.core.exceptions import ValidationError
from inspector.repository.node_repository import NodeRepository

logger = logging.getLogger(__name__)


class NodeService:

    def __init__(self):
        self.repository = NodeRepository()

    def get_node(self, id: str):
        node = self.repository.find_by_id(id)
        return NodeSerializer(node).data

    def get_nodes(self, only_normal):
        nodes = self.repository.find_all(only_normal)
        return [NodeSerializer(node).data for node in nodes]

    def add_node(self, node_data: Dict) -> Dict:
        try:
            username = node_data.get("username")
            port = int(node_data.get("port", 22))
            encrypted_ssh_password = node_data.get("ssh_password")
            decrypted_ssh_password = decryption.DecryptDecode(
                encrypted_ssh_password)
            ip_address = node_data.get("ip_address")
            node_label = node_data.get("node_label", {})
            if not self._is_node_label_valid(node_label):
                logger.error("node label is invalid")
                node_label = {}

            node, _ = self.repository.update_or_create(ip_address, {
                'port': port,
                'username': username,
                'ssh_password': decrypted_ssh_password,
                'node_label': node_label
            })

            return self._fetch_node_info(node)
        except Exception as e:
            logger.error(str(e))
            return {"status": "Failed", "ip_address": node_data.get("ip_address"), "reason": str(e)}

    def import_nodes(self, file_data: Dict):
        uploaded_file = file_data.get("file")
        if not uploaded_file:
            raise ValidationError("no file uploaded")
        thread = threading.Thread(
            target=self._process_nodes_in_background, args=(uploaded_file,))
        thread.start()

    def refresh_nodes(self, node_data: Dict):
        node_ids = node_data.get("node_ids", [])
        thread = threading.Thread(
            target=self._process_refresh_nodes_in_background, args=(node_ids,))
        thread.start()

    def modify_node(self, id: str, node_data: Dict):
        node = self.repository.find_by_id(id)
        node_label = node_data.get("node_label", {})
        if not self._is_node_label_valid(node_label):
            raise ValueError("node label is invalid")
        node.node_label = node_label
        self.repository.save(node)

    def modify_auth(self, id: str, node_data: Dict):
        node = self.repository.find_by_id(id)
        port = int(node_data.get("port", 22))
        username = node_data.get("username")
        encrypted_ssh_password = node_data.get("ssh_password")
        decrypted_ssh_password = decryption.DecryptDecode(
            encrypted_ssh_password)
        node.username = username
        node.ssh_password = decrypted_ssh_password
        node.port = port
        self.repository.save(node)
        return self._fetch_node_info(node)

    def delete_nodes(self, node_data: Dict):
        node_ids = node_data.get("node_ids", [])
        self.repository.delete_by_ids(node_ids)

    def _is_node_label_valid(self, node_label: dict):
        if len(node_label) > 20:
            return False
        for key, value in node_label.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return False
            if len(key) > 64 or len(value) > 64:
                return False
        return True

    def _fetch_node_info(self, node: models.Node) -> Dict:
        try:
            node_id = change_model_item_to_str(node.id)
            logger.info(f"start establish {node.ip_address} ssh trust...")
            node.is_accessible = False
            node_info = NodeInfo(node.ip_address, node.username,
                                 node.ssh_password, node.port)
            node.node_name = node_info.hostname
            node.gpu_manufacturer = node_info.gpu_manufacturer
            node.gpu_type = node_info.gpu_type
            node.gpu_count = node_info.gpu_count
            node.is_accessible = True
            self.repository.save(node)
            return {"status": "Success", "node_id": node_id}
        except Common_SSH_Exception as e:
            node.error_message = "failed to connect"
            self.repository.save(node)
            logger.error(str(e))
            return {"status": "Failed", "node_id": node_id, "reason": node.error_message}
        except Exception as e:
            node.error_message = str(e)
            self.repository.save(node)
            logger.error(str(e))
            return {"status": "Failed", "node_id": node_id, "reason": node.error_message}

    def _process_nodes_in_background(self, uploaded_file):
        """后台异步处理节点，并通过 WebSocket 发送结果"""
        try:
            csv_path = uploaded_file.temporary_file_path()

            field_mapping = {
                "ip地址": "ip_address",
                "ssh端口": "port",
                "ssh用户名": "username",
                "ssh密码": "ssh_password",
                "节点标签": "node_label",
                "dcgm端口": "dcgm_port",
            }
            data = []
            with open(csv_path, "r") as file:
                reader = csv.DictReader(file)
                new_fieldnames = [field_mapping.get(
                    field, field) for field in reader.fieldnames]
                reader.fieldnames = new_fieldnames
                for row in reader:
                    cleaned_row = {key: value.strip()
                                   for key, value in row.items()}
                    if cleaned_row["ip_address"] == "" or cleaned_row["port"] == "" or \
                            cleaned_row["username"] == "" or cleaned_row["ssh_password"] == "":
                        continue
                    if not is_valid_ip(cleaned_row["ip_address"]):
                        continue
                    cleaned_row["ssh_password"] = decryption.EncryptEncode(
                        cleaned_row["ssh_password"]
                    )
                    try:
                        cleaned_row["node_label"] = json.loads(
                            cleaned_row["node_label"])
                    except Exception:
                        cleaned_row["node_label"] = {}
                    data.append(cleaned_row)
            results = []
            failed_count = 0
            for row in data:
                row_result = self.add_node(row)
                if row_result["status"] == "Success":
                    results.append(row_result)
                else:
                    failed_count += 1

            if failed_count != 0:
                message = {
                    "type": "upload",
                    "status": "Failed",
                    "message": f"{len(results)} nodes added successfully, {failed_count} nodes failed.",
                }
            else:
                message = {
                    "type": "upload",
                    "status": "Success",
                    "message": f"all {len(results)} nodes added successfully.",
                }
            channel_layer = get_channel_layer()
            websocket_group = "node_manage_group"
            async_to_sync(channel_layer.group_send)(
                websocket_group, {"type": "message", "message": message}
            )
        except Exception as e:
            logger.error("Incorrect csv file content: %s", str(e))
            message = {"type": "upload", "status": "Error",
                       "message": "Incorrect csv file content"}
            channel_layer = get_channel_layer()
            websocket_group = "node_manage_group"
            async_to_sync(channel_layer.group_send)(
                websocket_group, {"type": "message", "message": message}
            )

    def _process_refresh_nodes_in_background(self, node_ids: List):
        for id in node_ids:
            try:
                node = self.repository.find_by_id(id)
                result = self._fetch_node_info(node)
                if result["status"] != "Success":
                    logger.error("refresh %s status: %s",
                                 id, result["reason"])
            except Exception as e:
                logger.error("refresh %s status: %s",
                             id, str(e))
        message = {
            "type": "refresh",
            "status": "Success",
            "message": "all nodes status refresh",
        }
        channel_layer = get_channel_layer()
        websocket_group = "node_manage_group"
        async_to_sync(channel_layer.group_send)(
            websocket_group, {"type": "message", "message": message}
        )
