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
import hashlib
from typing import Dict
from utils.consts import FileType, FileManageStatus, PathConfig
from inspector.serializers import CustomFileSerializer
from django.core.exceptions import ValidationError
from inspector.repository.file_repository import FileRepository


logger = logging.getLogger(__name__)


class FileService:

    def __init__(self):
        self.repository = FileRepository()

    def create_file_record(self, data: Dict):
        file_name = data.get("file_name")
        description = data.get("description", "")
        file_type = data.get("file_type")
        custom_file = self.repository.create(
            file_type=file_type,
            file_name=file_name,
            description=description
        )
        return CustomFileSerializer(custom_file).data

    def upload_file(self, file_id: str, file_data: Dict):
        uploaded_file = file_data.get("file")
        if not uploaded_file:
            raise ValidationError("No file provided for upload.")

        custom_file = self.repository.find_by_id(file_id)
        temp_path = uploaded_file.temporary_file_path()
        if custom_file.file_type == FileType.COMMON_FILE.value:
            dest_path = os.path.join(
                PathConfig.UPLOAD_COMMON_FILE_PATH, uploaded_file.name)
            os.rename(temp_path, dest_path)
        elif custom_file.file_type == FileType.TOOL_FILE.value:
            dest_path = os.path.join(
                PathConfig.UPLOAD_TOOL_FILE_PATH, uploaded_file.name)
            os.rename(temp_path, dest_path)
        elif custom_file.file_type == FileType.MODEL_FILE.value:
            dest_path = os.path.join(
                PathConfig.UPLOAD_MODEL_FILE_PATH, uploaded_file.name)
            os.rename(temp_path, dest_path)

        additional_info = self._generate_additional_info(dest_path)

        custom_file.file_size = uploaded_file.size
        custom_file.file_path = dest_path
        custom_file.status = FileManageStatus.UPLOADED.value
        custom_file.additional_info = additional_info
        self.repository.save(custom_file)
        return CustomFileSerializer(custom_file).data

    def edit_file(self, file_id: str, file_data: Dict):
        description = file_data.get("description")
        file_type = file_data.get("file_type")

        custom_file = self.repository.find_by_id(file_id)
        if description is not None:
            custom_file.description = description
        if file_type is not None:
            custom_file.file_type = file_type
        self.repository.save(custom_file)
        return CustomFileSerializer(custom_file).data

    def get_file(self, file_id: str):
        file = self.repository.find_by_id(file_id)
        return CustomFileSerializer(file).data

    def get_files(self):
        files = self.repository.find_all()
        return [CustomFileSerializer(file).data for file in files]

    def delete_file(self, file_id: str):
        custom_file = self.repository.find_by_id(file_id)
        if custom_file.file_path and os.path.exists(custom_file.file_path):
            os.remove(custom_file.file_path)
        self.repository.delete_by_ids([file_id])

    def _generate_additional_info(self, uploaded_file_path):
        additional_info = []
        md5_checksum = self._calculate_md5(uploaded_file_path)
        if md5_checksum:
            additional_info.append({"md5_checksum": md5_checksum})
        return additional_info

    def _calculate_md5(self, file_path):
        """计算给定文件路径的MD5哈希值"""
        hasher = hashlib.md5()
        block_size = 65536
        try:
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    hasher.update(block)
        except FileNotFoundError:
            logger.error(f"Error: The file '{file_path}' was not found.")
            return None
        except Exception as e:
            logger.error(f"An error occurred while reading the file: {e}")
            return None
        return hasher.hexdigest()
