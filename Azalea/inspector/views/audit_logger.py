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
from datetime import datetime
from functools import wraps
from typing import Optional

from django.contrib.auth.models import User


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self.logger = logging.getLogger('audit')

    def log_action(
        self,
        user: User,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
        status: str = "success"
    ):
        """
        记录用户操作

        Args:
            user: 执行操作的用户
            action: 操作类型 (create, update, delete, execute等)
            resource_type: 资源类型 (node, task, file等)
            resource_id: 资源 ID
            details: 额外详情
            status: 操作状态 (success, failed)
        """
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user.username,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "details": details or {}
        }

        self.logger.info(f"AUDIT: {audit_entry}")


_audit_logger = AuditLogger()


def extract_resource_id(request, resource_id_param: str, kwargs):
    if not resource_id_param:
        return
    resource_id = kwargs.get(resource_id_param)
    if resource_id is not None:
        return resource_id
    resource_id = request.GET.get(resource_id_param)
    if resource_id is not None:
        return resource_id
    try:
        resource_id = request.data.get(resource_id_param)
        return resource_id
    except Exception:
        return


def audit_log(resource_type: str, action: str, resource_id_param=""):
    """审计日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            resource_id = extract_resource_id(
                request, resource_id_param, kwargs)
            try:
                result = func(request, *args, **kwargs)
                _audit_logger.log_action(
                    user=request.user,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id or "N/A",
                    status="success"
                )
                return result

            except Exception as e:
                _audit_logger.log_action(
                    user=request.user,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id or "N/A",
                    status="failed",
                    details={"error": str(e)}
                )
                raise

        return wrapper
    return decorator
