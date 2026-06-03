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

from rest_framework import serializers
from inspector import models
from utils.tools import change_model_item_to_str


class NodeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = models.Node
        fields = [
            'id', 'node_name', 'username', 'ip_address',
            'port', 'node_label', 'gpu_manufacturer',
            'gpu_type', 'gpu_count', 'error_message',
            'is_accessible', 'created_at'
        ]

    def get_id(self, obj):
        return change_model_item_to_str(obj.id)

    def get_created_at(self, obj):
        return change_model_item_to_str(obj.created_at)


class EnvCheckItemSerializer(serializers.ModelSerializer):
    item_id = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = models.EnvCheckItem
        fields = [
            'item_id', 'parent', 'check_item', 'param',
            'status', 'msg', 'start_time', 'end_time'
        ]

    def get_item_id(self, obj):
        return change_model_item_to_str(obj.id)

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)


class EnvCheckNodeSerializer(serializers.ModelSerializer):
    node_id = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = models.EnvCheckNode
        fields = [
            'node_id', 'status', 'msg', 'start_time',
            'end_time'
        ]

    def get_node_id(self, obj):
        return change_model_item_to_str(obj.node_id)

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)


class EnvCheckTaskSerializer(serializers.ModelSerializer):
    task_id = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    items = EnvCheckItemSerializer(
        source='env_check_items',
        many=True,
        read_only=True
    )
    nodes = EnvCheckNodeSerializer(
        source='env_check_nodes',
        many=True,
        read_only=True
    )

    class Meta:
        model = models.EnvCheckTask
        fields = [
            'task_id', 'task_name', 'task_type', 'status',
            'msg', 'description', 'start_time', 'end_time',
            'updated_at', 'items', 'nodes'
        ]

    def __init__(self, *args, **kwargs):
        show_items = kwargs.pop('show_items', False)
        super().__init__(*args, **kwargs)
        if not show_items:
            self.fields.pop('items')
            self.fields.pop('nodes')

    def get_task_id(self, obj):
        return change_model_item_to_str(obj.id)

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)

    def get_updated_at(self, obj):
        return change_model_item_to_str(obj.updated_at)


class EnvCheckItemResultSerializer(serializers.ModelSerializer):
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = models.EnvCheckResult
        fields = [
            'nodes', 'status', 'start_time', 'end_time',
            'msg', 'detail_result', 'format_result'
        ]

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)


class EnvCheckNodeResultSerializer(serializers.ModelSerializer):
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    check_item = serializers.SerializerMethodField()
    param = serializers.SerializerMethodField()

    class Meta:
        model = models.EnvCheckResult
        fields = [
            'status', 'start_time', 'end_time',
            'msg', 'detail_result', 'format_result',
            'parent', 'check_item', 'param'
        ]

    def __init__(self, *args, **kwargs):
        self.item_info = kwargs.pop('item_info', {})
        super().__init__(*args, **kwargs)

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)

    def get_parent(self, obj):
        return self.item_info.get('parent')

    def get_check_item(self, obj):
        return self.item_info.get('check_item')

    def get_param(self, obj):
        return self.item_info.get('param')


class ModelNodeTaskSerializer(serializers.ModelSerializer):
    node_name = serializers.SerializerMethodField()
    node_id = serializers.SerializerMethodField()
    gpu_manufacturer = serializers.SerializerMethodField()
    gpu_type = serializers.SerializerMethodField()
    gpu_count = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    estimated_end_time = serializers.SerializerMethodField()

    class Meta:
        model = models.NodeModelTask
        fields = [
            'task_type', 'node_name', 'node_id', 'gpu_manufacturer',
            'gpu_type', 'gpu_count', 'status', 'progress',
            'msg', 'start_time', 'end_time', 'estimated_end_time',
            'target_result', 'task_result', 'task_param'
        ]

    def get_node_name(self, obj):
        return obj.node.node_name

    def get_node_id(self, obj):
        return change_model_item_to_str(obj.node.id)

    def get_gpu_manufacturer(self, obj):
        return obj.node.gpu_manufacturer

    def get_gpu_type(self, obj):
        return obj.node.gpu_type

    def get_gpu_count(self, obj):
        return obj.node.gpu_count

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)

    def get_estimated_end_time(self, obj):
        return change_model_item_to_str(obj.estimated_end_time)


class ModelTaskSerializer(serializers.ModelSerializer):
    task_id = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    node_infos = ModelNodeTaskSerializer(
        source='node_model_tasks',
        many=True,
        read_only=True
    )

    class Meta:
        model = models.ModelTask
        fields = [
            'task_id', 'task_name', 'task_type', 'remote_data_path',
            'status', 'start_time', 'end_time', 'updated_at',
            'node_infos'
        ]

    def get_task_id(self, obj):
        return change_model_item_to_str(obj.id)

    def get_start_time(self, obj):
        return change_model_item_to_str(obj.start_time)

    def get_end_time(self, obj):
        return change_model_item_to_str(obj.end_time)

    def get_updated_at(self, obj):
        return change_model_item_to_str(obj.updated_at)


class CustomFileSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = models.CustomFile
        fields = [
            'id', 'file_type', 'file_name', 'description',
            'file_size', 'status', 'additional_info', 'created_at',
            'updated_at'
        ]

    def get_id(self, obj):
        return change_model_item_to_str(obj.id)

    def get_created_at(self, obj):
        return change_model_item_to_str(obj.created_at)

    def get_updated_at(self, obj):
        return change_model_item_to_str(obj.updated_at)
