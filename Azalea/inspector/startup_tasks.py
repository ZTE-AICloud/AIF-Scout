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

import threading
import time
import logging
import django

logger = logging.getLogger(__name__)


class DelayedTaskRestorer:
    def __init__(self, delay_seconds=2.0):
        self.delay_seconds = delay_seconds
        self._started = False
        self._lock = threading.Lock()
        self._tasks = []

    def add_task(self, func):
        self._tasks.append(func)

    def start(self):
        def delayed_start():
            logger.info("Waiting for Django apps to be ready...")
            while not django.apps.apps.ready:
                time.sleep(0.5)
            with self._lock:
                if self._started:
                    logger.info("Startup tasks already started, skipping.")
                    return
                self._started = True
            logger.info("Starting registered startup tasks...")
            for task in self._tasks:
                try:
                    threading.Thread(target=task, daemon=True).start()
                    logger.info(f"Started task: {task.__name__}")
                except Exception as e:
                    logger.error(
                        f"Failed to start task {task.__name__}: {str(e)}")
        timer = threading.Timer(self.delay_seconds, delayed_start)
        timer.daemon = True
        timer.start()
