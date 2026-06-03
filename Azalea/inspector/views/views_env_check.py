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

from django.http import StreamingHttpResponse

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view

from utils import files
from inspector.services.env_check_service import EnvCheckService

import os
import logging
from inspector.views.exceptions import handle_exceptions
from inspector.views.audit_logger import audit_log


env_check_service = EnvCheckService()

logger = logging.getLogger(__name__)


@api_view(["GET"])
@handle_exceptions("Failed to get env check tasks")
@audit_log(resource_type="env_check", action="list")
def get_check_tasks(request: Request) -> Response:
    """获取所有检测任务"""
    task_type = request.query_params.get("task_type")
    return Response(env_check_service.get_check_tasks(task_type))


@api_view(["GET"])
@handle_exceptions("Failed to get env check task")
@audit_log(resource_type="env_check", action="get", resource_id_param="task_id")
def get_check_task(request: Request, task_id: str) -> Response:
    """获取单个检测任务"""
    return Response(env_check_service.get_check_task(task_id))


@api_view(["POST"])
@handle_exceptions("Failed to delete env check task")
@audit_log(resource_type="env_check", action="delete", resource_id_param="task_ids")
def delete_check_tasks(request: Request) -> Response:
    """删除检测任务"""
    env_check_service.delete_check_tasks(request.data)
    return Response(
        {"message": "Check tasks are deleted successfully"}
    )


@api_view(["POST"])
@handle_exceptions("Failed to create env check task")
@audit_log(resource_type="env_check", action="create")
def create_task(request: Request) -> Response:
    task_id = env_check_service.create_check_task(request.data)
    return Response({"task_id": task_id})


@api_view(["POST"])
@handle_exceptions("Failed to modify env check task")
@audit_log(resource_type="env_check", action="modify", resource_id_param="task_id")
def modify_task(request: Request, task_id: str) -> Response:
    env_check_service.modify_check_task(task_id, request.data)
    return Response(
        {"message": "modify task successfully."}
    )


@api_view(["POST"])
@handle_exceptions("Failed to execute env check task")
@audit_log(resource_type="env_check", action="execute", resource_id_param="task_id")
def execute_task(request: Request, task_id: str) -> Response:
    env_check_service.execute_check_task(task_id)
    return Response(
        {"message": "Execute task successfully."}
    )


@api_view(["POST"])
@handle_exceptions("Failed to stop env check task")
@audit_log(resource_type="env_check", action="stop", resource_id_param="task_id")
def stop_task(request: Request, task_id: str) -> Response:
    env_check_service.stop_check_task(task_id)
    return Response(
        {"message": "Check task is stopping."}
    )


@api_view(["GET"])
@handle_exceptions("Failed to get env check item result")
@audit_log(resource_type="env_check_item", action="view", resource_id_param="task_id")
def get_check_item_result(request: Request, task_id: str, item_id: str) -> Response:
    res = {
        "results": env_check_service.get_check_item_result(task_id, item_id),
    }
    return Response(res)


@api_view(["GET"])
@handle_exceptions("Failed to get env check node result")
@audit_log(resource_type="env_check_node", action="view", resource_id_param="task_id")
def get_check_node_result(request: Request, task_id: str, node_id: str) -> Response:
    res = {
        "items": env_check_service.get_check_node_result(task_id, node_id),
    }
    return Response(res)


@api_view(["POST"])
@handle_exceptions("Failed to download env check result")
@audit_log(resource_type="env_check", action="download", resource_id_param="task_id")
def download_env_check_log(request: Request) -> Response:
    result_path = env_check_service.download_env_check_log(request.data)
    file_name = os.path.basename(result_path)
    response = StreamingHttpResponse(
        files.file_iterator_response(result_path))
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response
