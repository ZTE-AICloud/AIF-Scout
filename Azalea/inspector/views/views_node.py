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
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from inspector.services.node_service import NodeService
from inspector.views.exceptions import handle_exceptions
from rest_framework import status
from inspector.views.audit_logger import audit_log

node_service = NodeService()

logger = logging.getLogger(__name__)


@api_view(["GET"])
@handle_exceptions("Get node failed")
@audit_log(resource_type="node", action="get", resource_id_param="id")
def get_node(request, id: str):
    return Response(node_service.get_node(id))


@api_view(["GET"])
@handle_exceptions("Get nodes failed")
@audit_log(resource_type="node", action="list")
def list_nodes(request):
    query_normal = request.GET.get("normal")
    node_list = node_service.get_nodes(query_normal == "true")
    return Response({"nodes": node_list})


@api_view(["POST"])
@handle_exceptions("Add node failed")
@audit_log(resource_type="node", action="create")
def add_node(request: Request) -> Response:
    """添加单个节点"""
    result = node_service.add_node(request.data)
    if result["status"] == "Success":
        return Response({"node_id": result["node_id"]})
    else:
        raise Exception(result["reason"])


@api_view(["POST"])
@handle_exceptions("Import node failed")
@audit_log(resource_type="node", action="batch_create")
def add_node_batches(request):
    """批量添加节点，并通过 WebSocket 推送处理结果"""
    node_service.import_nodes(request.FILES)
    return Response({"message": "Processing started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@handle_exceptions("Refresh node failed")
@audit_log(resource_type="node", action="refresh", resource_id_param="node_ids")
def refresh_node_status_batches(request):
    node_service.refresh_nodes(request.data)
    return Response({"message": "Processing started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@handle_exceptions("Modify node failed")
@audit_log(resource_type="node", action="modify", resource_id_param="id")
def modify_node(request, id: str):
    node_service.modify_node(id, request.data)
    return Response({"message": "node modify successfully"})


@api_view(["POST"])
@handle_exceptions("Modify node auth failed")
@audit_log(resource_type="node", action="modify_auth", resource_id_param="id")
def modify_auth(request, id: str):
    result = node_service.modify_auth(id, request.data)
    if result["status"] == "Success":
        return Response({"status": "success"})
    else:
        raise Exception(result["reason"])


@api_view(["POST"])
@handle_exceptions("Delete nodes failed")
@audit_log(resource_type="node", action="delete", resource_id_param="node_ids")
def delete_node_batches(request):
    node_service.delete_nodes(request.data)
    return Response(
        {"message": "delete nodes successfully"}
    )
