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
from inspector.services.file_service import FileService
from inspector.views.exceptions import handle_exceptions
from inspector.views.audit_logger import audit_log


logger = logging.getLogger(__name__)


file_service = FileService()


@api_view(["POST"])
@handle_exceptions("Create file record failed")
@audit_log(resource_type="file", action="create")
def create_file_record(request: Request) -> Response:
    res = file_service.create_file_record(request.data)
    return Response({"file": res})


@api_view(["POST"])
@handle_exceptions("Upload file record failed")
@audit_log(resource_type="file", action="upload", resource_id_param="id")
def upload_file(request: Request, id: str):
    res = file_service.upload_file(id, request.FILES)
    return Response(
        {"message": "File uploaded successfully", "file": res}
    )


@api_view(["POST"])
@handle_exceptions("Edit file record failed")
@audit_log(resource_type="file", action="modify", resource_id_param="id")
def edit_file(request: Request, id: str):
    res = file_service.edit_file(id, request.data)
    return Response({"message": "File edit successfully", "file": res})


@api_view(["GET"])
@handle_exceptions("Get files record failed")
@audit_log(resource_type="file", action="list")
def get_file_list(request: Request) -> Response:
    res = file_service.get_files()
    return Response({"files": res})


@api_view(["GET"])
@handle_exceptions("Get file record failed")
@audit_log(resource_type="file", action="get", resource_id_param="id")
def get_file(request: Request, id: str) -> Response:
    res = file_service.get_file(id)
    return Response({"file": res})


@api_view(["POST"])
@handle_exceptions("Delete files record failed")
@audit_log(resource_type="file", action="delete", resource_id_param="id")
def delete_file_record(request: Request, id: str) -> Response:
    file_service.delete_file(id)
    return Response({"message": "File deleted successfully"})
