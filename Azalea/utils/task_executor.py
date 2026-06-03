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

import re
import threading

import logging


from typing import List
from threading import Thread

logger = logging.getLogger(__name__)
# event: Event = Event()  # event.isSet() initial value is False, locked status


class SerializeTasks(threading.Thread):
    def __init__(self, name, threads):
        threading.Thread.__init__(self)

        self.setName(name)
        self.thread_stop = False
        self.threads: List[Thread] = threads

    def run(self):
        logger.info(f"Start thread {self.getName()}")

        for t in self.threads:
            if self.thread_stop:
                break

            t.start()
            t.join()
            # if event.is_set() is False:
            #     event.wait()
            #     print('wait')
            #     time.sleep(1)

    def stop(self):
        for t in self.threads:
            if t.is_alive():
                t.stop()

        self.thread_stop = True


# class SerializeProcess(multiprocessing.Process):
#     def __init__(self, name, processes):
#         multiprocessing.Process.__init__(self)
#         self.name = name
#         self.processes: List[multiprocessing.Process] = processes

#     def run(self):
#         print(f"Start process {self.name}")

#         for p in self.processes:
#             p.start()
#             p.join()

#     def stop(self):
#         for p in self.processes:
#             if p.is_alive():
#                 p.terminate()


def thread_print(text):
    print("[%s]: %s" % (threading.currentThread().getName(), text))


def validate_task_name(name: str) -> bool:
    """
    校验任务名称是否符合规则：
    - 首字符必须是字母（a-z, A-Z）
    - 后续字符可以是字母、数字、下划线(_)或连字符(-)
    - 总长度不超过64个字符（1-64字符）
    """
    # 原始字符串直接包含正则表达式，^锚定开头，$锚定结尾
    pattern = r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$"
    return bool(re.fullmatch(pattern, name))
