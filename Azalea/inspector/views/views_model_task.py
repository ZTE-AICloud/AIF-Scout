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

import os

from django.http import StreamingHttpResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
import logging

from utils import files
from inspector.services.model_task_service import ModelTaskService
from inspector.views.exceptions import handle_exceptions
from inspector.views.audit_logger import audit_log

model_task_service = ModelTaskService()


logger = logging.getLogger(__name__)


@api_view(["GET"])
@handle_exceptions("Get model tasks failed")
@audit_log(resource_type="model_task", action="list")
def get_model_tasks(request: Request) -> Response:
    """获取所有模型任务"""
    return Response(model_task_service.get_model_tasks())


@api_view(["GET"])
@handle_exceptions("Get model task failed")
@audit_log(resource_type="model_task", action="get", resource_id_param="task_id")
def get_single_model_task(request: Request, task_id: str) -> Response:
    """获取单个模型任务"""
    return Response(model_task_service.get_model_task(task_id))


@api_view(["POST"])
@handle_exceptions("Delete model tasks failed")
@audit_log(resource_type="model_task", action="delete", resource_id_param="task_ids")
def delete_model_tasks(request: Request) -> Response:
    """删除模型任务"""
    model_task_service.delete_model_tasks(request.data)
    return Response(
        {"message": "Model tasks  are deleted successfully"}
    )


@api_view(["POST"])
@handle_exceptions("Create model task failed")
@audit_log(resource_type="model_task", action="create")
def create_model_task(request: Request) -> Response:
    return Response({"task_id": model_task_service.create_model_task(request.data)})


@api_view(["POST"])
@handle_exceptions("Excute model task failed")
@audit_log(resource_type="model_task", action="execute", resource_id_param="task_id")
def execute_model_task(request: Request) -> Response:
    """执行模型任务"""
    return Response({"task_id": model_task_service.execute_model_task(request.data)})


@api_view(["POST"])
@handle_exceptions("Download model task result failed")
@audit_log(resource_type="model_task", action="download", resource_id_param="task_id")
def download_result(request: Request) -> Response:
    """下载任务结果"""
    result_path = model_task_service.download_result(request.data)
    file_name = os.path.basename(result_path)
    response = StreamingHttpResponse(
        files.file_iterator_response(result_path))
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@api_view(["POST"])
@handle_exceptions("Get model task result failed")
@audit_log(resource_type="model_task", action="view", resource_id_param="task_id")
def view_result(request: Request) -> Response:
    return Response({"result": model_task_service.view_result(request.data)})


@api_view(["POST"])
@handle_exceptions("Stop model task failed")
@audit_log(resource_type="model_task", action="stop", resource_id_param="task_id")
def stop_model_task(request: Request) -> Response:
    model_task_service.stop_model_task(request.data)
    return Response({"message": "Model task is stopping."})
