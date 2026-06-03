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
from django.db.models import Prefetch


class ModelTaskRepository:

    def find_by_id(self, id: str) -> models.ModelTask:
        return models.ModelTask.objects.get(id=id)

    def find_by_ids(self, ids: str) -> List[models.ModelTask]:
        query = models.ModelTask.objects.filter(id__in=ids).prefetch_related(
            Prefetch(
                'node_model_tasks',
                queryset=models.NodeModelTask.objects.select_related(
                    'node')
            )
        )
        return query

    def find_all(self) -> List[models.ModelTask]:
        query = models.ModelTask.objects.all().prefetch_related(
            Prefetch(
                'node_model_tasks',
                queryset=models.NodeModelTask.objects.select_related(
                    'node')
            )
        )
        return query

    def find_by_statuses(self, statuses: List[str]) -> List[models.ModelTask]:
        query = models.ModelTask.objects.filter(status__in=statuses).prefetch_related(
            Prefetch(
                'node_model_tasks',
                queryset=models.NodeModelTask.objects.select_related(
                    'node')
            )
        )
        return query

    @transaction.atomic
    def create(self, task_name: str, task_type: str, remote_data_path: str) -> models.ModelTask:
        return models.ModelTask.objects.create(
            task_name=task_name,
            task_type=task_type,
            remote_data_path=remote_data_path
        )

    @transaction.atomic
    def save(self, model: models.ModelTask):
        model.save()

    @transaction.atomic
    def delete(self, model: models.ModelTask):
        model.delete()


class NodeModelTaskRepository:

    def find_all(self, task_id: str) -> List[models.NodeModelTask]:
        query = models.NodeModelTask.objects.filter(
            task_id=task_id).select_related('node')
        return query

    def find_by_statuses(self, task_id: str, statuses: List[str]) -> List[models.NodeModelTask]:
        query = models.NodeModelTask.objects.filter(
            task_id=task_id, status__in=statuses).select_related('node')
        return query

    def find_by_statuses_and_id(self, node_id: str, statuses: List[str], task_type: str) -> List[models.NodeModelTask]:
        node_tasks = models.NodeModelTask.objects.filter(
            node_id=node_id,
            status__in=statuses
        )
        if task_type:
            node_tasks.filter(task_type=task_type)
        return node_tasks

    @transaction.atomic
    def save(self, node_model: models.NodeModelTask):
        node_model.save()
