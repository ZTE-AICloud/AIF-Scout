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

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import permissions

from inspector.services.system_service import SystemService
from inspector.views.exceptions import handle_exceptions
from inspector.views.audit_logger import audit_log

system_service = SystemService()

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([])
@permission_classes((permissions.AllowAny,))
@handle_exceptions("Login failed")
@audit_log(resource_type="system", action="login")
def login_view(request: Request) -> Response:
    res = system_service.login(request)
    return Response(res)


@api_view(["GET"])
@handle_exceptions("Logout failed")
@audit_log(resource_type="system", action="logout")
def logout_view(request):
    system_service.logout(request)
    return Response({"status": "success"})


@api_view(["POST"])
@handle_exceptions("Change password failed")
@audit_log(resource_type="system", action="modyfiy_auth")
def change_password(request: Request) -> Response:
    """
    修改密码功能
    要求用户已登录
    新密码必须符合强度要求:
    - 至少8个字符
    - 包含大写字母
    - 包含小写字母
    - 包含数字
    - 包含特殊字符
    """
    res = system_service.change_login_password(request)
    return Response(res)


@api_view(["POST"])
@handle_exceptions("Get config from file failed")
@audit_log(resource_type="system", action="get_config", resource_id_param="file")
def get_config_from_file(request: Request) -> Response:
    res = system_service.get_config_from_file(request.data)
    return Response({"configContent": res})
