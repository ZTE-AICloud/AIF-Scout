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

from django.apps import AppConfig
from inspector.startup_tasks import DelayedTaskRestorer


class InspectorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inspector"

    def ready(self):
        from model_task.model_tasks_restore import restore_model_tasks
        from env_check.restore import restore_env_check_tasks

        restorer = DelayedTaskRestorer(delay_seconds=2.0)
        restorer.add_task(restore_model_tasks)
        restorer.add_task(restore_env_check_tasks)
        restorer.start()
