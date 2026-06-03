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

from django.urls import path
from inspector.views import views_node, views_env_check, views_model_task, views_file, views_system

urlpatterns = [
    path("login/", views_system.login_view, name="login"),
    path("logout/", views_system.logout_view, name="logout"),
    path("change_password/", views_system.change_password, name="change_password"),
    path("nodes/get/<str:id>/", views_node.get_node, name="get_node"),
    path("nodes/", views_node.list_nodes, name="get_node_list"),
    path("nodes/add/", views_node.add_node, name="add_node"),
    path("nodes/batch_add/", views_node.add_node_batches,
         name="add_node_batches"),
    path("nodes/modifyLabel/<str:id>/",
         views_node.modify_node, name="modify_node"),
    path("nodes/modifyAuth/<str:id>/",
         views_node.modify_auth, name="modify_auth"),
    path("nodes/batch_delete/", views_node.delete_node_batches,
         name="delete_node_batches"),
    path("nodes/batch_refresh/", views_node.refresh_node_status_batches,
         name="refresh_node_status_batches"),
    path("fileConfig/", views_system.get_config_from_file, name="get_file_config"),
    path("env_check/tasks/", views_env_check.get_check_tasks,
         name="get_env_check_tasks"),
    path(
        "env_check/tasks/<str:task_id>", views_env_check.get_check_task, name="get_env_check_task"
    ),
    path("env_check/tasks/create/", views_env_check.create_task,
         name="create_env_check_task"),
    path("env_check/tasks/modify/<str:task_id>", views_env_check.modify_task,
         name="modify_env_check_task"),
    path(
        "env_check/tasks/execute/<str:task_id>",
        views_env_check.execute_task,
        name="execute_env_check_task",
    ),
    path(
        "env_check/tasks/stop/<str:task_id>", views_env_check.stop_task, name="stop_env_check_task"
    ),
    path(
        "env_check/tasks/delete/", views_env_check.delete_check_tasks, name="delete_env_check_tasks"
    ),
    path(
        "env_check/task/<str:task_id>/items/<str:item_id>/result/",
        views_env_check.get_check_item_result,
        name="get_env_check_item_result",
    ),
    path(
        "env_check/task/<str:task_id>/node/<str:node_id>/result/",
        views_env_check.get_check_node_result,
        name="get_env_check_node_result",
    ),
    path("env_check/tasks/log_download/",
         views_env_check.download_env_check_log, name="download_env_check_log"),
    path("files/", views_file.get_file_list, name="get files record"),
    path("files/get/<str:id>/", views_file.get_file, name="get file record"),
    path("files/add/", views_file.create_file_record, name="create file record"),
    path("files/edit/<str:id>/", views_file.edit_file, name="edit file record"),
    path("files/delete/<str:id>/", views_file.delete_file_record,
         name="create file record"),
    path("files/upload/<str:id>/", views_file.upload_file, name="upload file"),
    path("modelTask/list/", views_model_task.get_model_tasks, name="get model tasks"),
    path(
        "modelTask/detail/<str:task_id>",
        views_model_task.get_single_model_task,
        name="get single model task",
    ),
    path("modelTask/delete/", views_model_task.delete_model_tasks,
         name="delete model tasks"),
    path("modelTask/create/", views_model_task.create_model_task,
         name="create model tasks"),
    path("modelTask/execute/", views_model_task.execute_model_task,
         name="execute model tasks"),
    path(
        "modelTask/download_result/", views_model_task.download_result, name="download task result"
    ),
    path("modelTask/view_result/",
         views_model_task.view_result, name="view task result"),
    path("modelTask/stop/", views_model_task.stop_model_task, name="stop model task"),
]
