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

assert torch.cuda.is_available()


def host_to_device_bandwidth_benchmark() -> float:
    x = torch.randn((1024, 1024, 1024), device="cuda", dtype=torch.float32)
    y = torch.ones_like(x, device="cpu", dtype=torch.float32, pin_memory=True)
    torch.cuda.synchronize()

    start_event = torch.cuda.Event(enable_timing=True)
    end_event = torch.cuda.Event(enable_timing=True)

    start_event.record()
    # copy from y to x (cpu -> cuda)
    x.copy_(y)
    torch.cuda.synchronize()
    end_event.record()
    end_event.synchronize()

    # GB/s
    bandwidth = (
        x.nelement() * x.element_size() * 1e-9 /
        (start_event.elapsed_time(end_event) * 1e-3)
    )
    del x, y
    return round(bandwidth, 2)


if __name__ == "__main__":
    for gpu_id in range(torch.cuda.device_count()):
        with torch.cuda.device(f"cuda:{gpu_id}"):
            bandwidth = host_to_device_bandwidth_benchmark()
            print(f"host -> gpu {gpu_id}: {bandwidth}")
