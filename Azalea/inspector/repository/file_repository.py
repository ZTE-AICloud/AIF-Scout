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

from typing import List
from inspector import models
from django.db import transaction


class FileRepository:

    def create(self, file_type: str, file_name: str, description: str) -> models.CustomFile:
        return models.CustomFile.objects.create(
            file_type=file_type,
            file_name=file_name,
            description=description
        )

    def find_by_id(self, id: str) -> models.CustomFile:
        return models.CustomFile.objects.get(id=id)

    def find_all(self) -> List[models.CustomFile]:
        return models.CustomFile.objects.all()

    @transaction.atomic
    def save(self, file: models.CustomFile):
        file.full_clean()
        file.save()

    @transaction.atomic
    def delete_by_ids(self, ids: str):
        models.CustomFile.objects.filter(id__in=ids).delete()
