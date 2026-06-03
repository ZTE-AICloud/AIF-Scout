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


class NodeRepository:

    def find_by_id(self, node_id: str) -> models.Node:
        return models.Node.objects.get(id=node_id)

    def find_by_ids(self, node_ids: str) -> List[models.Node]:
        return models.Node.objects.filter(id__in=node_ids)

    def find_all(self, accessible_only: bool = False) -> List[models.Node]:
        query = models.Node.objects.all()
        if accessible_only:
            query = query.filter(is_accessible=True)
        return query

    @transaction.atomic
    def update_or_create(self, ip_address: str, defaults: dict) -> tuple[models.Node, bool]:
        return models.Node.objects.update_or_create(
            ip_address=ip_address,
            defaults=defaults,
        )

    @transaction.atomic
    def save(self, node: models.Node):
        node.full_clean()
        node.save()

    @transaction.atomic
    def delete_by_ids(self, node_ids: List[str]):
        models.Node.objects.filter(id__in=node_ids).delete()
