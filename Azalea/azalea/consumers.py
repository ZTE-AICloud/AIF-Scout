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
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync


class WSConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = self.scope["url_route"]["kwargs"]["group_name"]

        # Join group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        # Leave group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name)

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.group_name, {"type": "send", "message": message}
        )

    # Receive message from group
    def message(self, event):
        message = event["message"]
        if isinstance(message, dict):
            message = json.dumps(message)
        # Send message to WebSocket
        self.send(text_data=message)
