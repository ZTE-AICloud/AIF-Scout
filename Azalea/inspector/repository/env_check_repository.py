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


class EnvCheckTaskRepository:

    def find_by_id(self, id: str) -> models.EnvCheckTask:
        return models.EnvCheckTask.objects.get(id=id)

    def find_by_ids(self, ids: str) -> List[models.EnvCheckTask]:
        query = models.EnvCheckTask.objects.filter(id__in=ids).prefetch_related(
            'env_check_items',
            'env_check_nodes',
            'env_check_results'
        )
        return query

    def find_all(self, task_type: str) -> List[models.EnvCheckTask]:
        query = models.EnvCheckTask.objects.all()
        if task_type:
            query = query.filter(task_type=task_type)
        query = query.prefetch_related(
            'env_check_items',
            'env_check_nodes',
            'env_check_results'
        )
        return query

    def find_by_statuses(self, statuses: List[str]) -> models.EnvCheckTask:
        query = models.EnvCheckTask.objects.filter(status__in=statuses).prefetch_related(
            'env_check_items',
            'env_check_nodes',
            'env_check_results'
        )
        return query

    @transaction.atomic
    def create(self, task_name: str, task_type: str, nodes: List[str], description: str) -> models.EnvCheckTask:
        return models.EnvCheckTask.objects.create(
            task_name=task_name,
            task_type=task_type,
            nodes=nodes,
            description=description,
        )

    @transaction.atomic
    def save(self, check_task: models.EnvCheckTask):
        check_task.save()

    @transaction.atomic
    def delete(self, check_task: models.EnvCheckTask):
        check_task.delete()


class EnvCheckItemRepository:

    def find_by_id(self, task_id: str, id: str) -> List[models.EnvCheckItem]:
        return models.EnvCheckItem.objects.filter(task_id=task_id, id=id)

    def find_by_statuses(self, task_id: str, statuses: List[str]) -> List[models.EnvCheckItem]:
        return models.EnvCheckItem.objects.filter(task_id=task_id, status__in=statuses)

    def find_all(self, task_id: str) -> List[models.EnvCheckItem]:
        return models.EnvCheckItem.objects.filter(task_id=task_id)

    def find_by_item_id(self, item_id: str) -> List[models.EnvCheckItem]:
        return models.EnvCheckResult.objects.filter(item_id=item_id)

    @transaction.atomic
    def create(self, task: models.EnvCheckTask, parent: str, check_item: str, param) -> models.EnvCheckItem:
        return models.EnvCheckItem.objects.create(
            task=task,
            parent=parent,
            check_item=check_item,
            param=param
        )

    @transaction.atomic
    def save(self, check_item: models.EnvCheckItem):
        check_item.save()


class EnvCheckNodeRepository:

    def find_by_ids(self, task_id: str, ids: str) -> List[models.EnvCheckNode]:
        return models.EnvCheckNode.objects.filter(task_id=task_id, node_id__in=ids)

    def find_by_statuses(self, task_id: str, statuses: List[str]) -> List[models.EnvCheckNode]:
        return models.EnvCheckNode.objects.filter(task_id=task_id, status__in=statuses)

    def find_all(self, task_id: str) -> List[models.EnvCheckNode]:
        return models.EnvCheckNode.objects.filter(task_id=task_id)

    @transaction.atomic
    def create(self, task: models.EnvCheckTask, node_id: str) -> models.EnvCheckNode:
        return models.EnvCheckNode.objects.create(
            task=task,
            node_id=node_id,
        )

    @transaction.atomic
    def save(self, check_node: models.EnvCheckNode):
        check_node.save()


class EnvCheckResultRepository:

    def find_all(self, task_id: str) -> List[models.EnvCheckResult]:
        return models.EnvCheckResult.objects.filter(
            task_id=task_id).select_related('item')

    @transaction.atomic
    def delete_all(self, check_task: models.EnvCheckTask):
        check_task.env_check_results.all().delete()

    @transaction.atomic
    def save(self, check_result: models.EnvCheckResult):
        check_result.full_clean()
        check_result.save()
