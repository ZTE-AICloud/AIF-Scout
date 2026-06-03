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

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import BadRequest, PermissionDenied, RequestAborted, ValidationError
from django.middleware.csrf import get_token
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from axes.handlers.proxy import AxesProxyHandler

from utils import decryption
from utils.consts import PathConfig
from inspector.repository.custom_user_repository import CustomUserRepository

logger = logging.getLogger(__name__)


class SystemService:

    def __init__(self):
        self.user_repository = CustomUserRepository()

    def login(self, request):
        try:
            if request.method != "POST":
                raise BadRequest("Only POST requests are allowed")
            # 解析用户名和密码
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
            password = decryption.DecryptDecode(password)

            if not username or not password:
                raise BadRequest("Username and password are required")

            if AxesProxyHandler().is_locked(request, {'username': username}):
                raise RequestAborted(
                    "Account locked due to too many failed attempts. Try again in 30 minutes.")

            users = self.user_repository.find_all()
            if len(users) == 0:  # 系统尚无用户时自动创建
                self._validate_password_strength(password)
                user = self.user_repository.create(
                    username=username,
                    password=password
                )
                logger.info(f"Initial user created: {username}")
            # 尝试认证
            user = authenticate(
                request, username=username, password=password)

            if user is not None:
                self._refreshSession(request)
                login(request, user)
                refresh = RefreshToken.for_user(user)
                return {
                    "status": "success",
                    "refresh_token": str(refresh),
                    "access_token": str(refresh.access_token),
                    "csrfToken": get_token(request)
                }
            else:
                logger.error("authenticate failed")
                raise PermissionDenied("Invalid credentials")

        except Exception as e:
            self._refreshSession(request)
            raise e

    def logout(self, request):
        logout(request)

    def change_login_password(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied("User is not authenticated")
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        old_password = decryption.DecryptDecode(old_password)
        new_password = decryption.DecryptDecode(new_password)

        if not old_password or not new_password:
            raise BadRequest("Both old and new passwords are required")
        if old_password == new_password:
            raise BadRequest(
                "The new password cannot be the same as the old one")

        # 验证旧密码
        user = authenticate(
            request=request, username=request.user.username, password=old_password)
        if user is None:
            raise PermissionDenied("Invalid old password")

        self._validate_password_strength(new_password)
        user.set_password(new_password)
        self.user_repository.save(user)
        logout(request)

    def _refreshSession(self, request: Request):
        request.session.flush()
        request.session.create()

    def _validate_password_strength(self, password):
        if len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long.")

        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                "Password must contain at least one uppercase letter.")

        if not re.search(r'[a-z]', password):
            raise ValidationError(
                "Password must contain at least one lowercase letter.")

        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one digit.")

        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                "Password must contain at least one special character.")

    def get_config_from_file(self, data):
        file_path = PathConfig.ETC_DIR / data.get("file")
        with open(file_path, "r") as file:
            content = file.read()
        return content
