#!/usr/bin/python
#
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

import torch
import time
from torch import cuda


assert torch.cuda.is_available()


def memory_bandwidth_benchmark() -> float:
    elapsed_time = 0
    size = int(1024 * 1024 * 1024)

    # Create random tensors
    a = torch.rand(size, device="cuda")
    b = torch.rand(size, device="cuda")

    # Warm-up
    cuda.synchronize()
    a.copy_(b)
    cuda.synchronize()

    start_time = time.time()
    a.copy_(b)
    cuda.synchronize()
    end_time = time.time()

    elapsed_time = end_time - start_time

    bytes_copied = a.nelement() * a.element_size()  # bytes
    bandwidth = 2 * bytes_copied / elapsed_time / 1e9  # GB/s

    return round(bandwidth, 2)


if __name__ == "__main__":
    for gpu_id in range(torch.cuda.device_count()):
        with torch.cuda.device(f"cuda:{gpu_id}"):
            bandwidth = memory_bandwidth_benchmark()
            print(f"gpu {gpu_id}: {bandwidth}")
