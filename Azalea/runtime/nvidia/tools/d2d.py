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

from itertools import combinations
import torch

assert torch.cuda.is_available()
assert torch.cuda.device_count() >= 2


def device_to_device_bandwidth_benchmark(src_id, dest_id) -> float:
    x = torch.randn((1024, 1024, 1024), device=f"cuda:{src_id}")
    y = torch.rand_like(x, device=f"cuda:{dest_id}")

    torch.cuda.synchronize(src_id)
    torch.cuda.synchronize(dest_id)

    start_event = torch.cuda.Event(enable_timing=True)
    end_event = torch.cuda.Event(enable_timing=True)

    start_event.record()

    # copy from x to y
    y.copy_(x)
    torch.cuda.synchronize(src_id)
    torch.cuda.synchronize(dest_id)
    end_event.record()
    end_event.synchronize()

    bandwidth = (
        x.nelement() * x.element_size() * 1e-9 /
        (start_event.elapsed_time(end_event) * 1e-3)
    )
    del x, y
    return round(bandwidth, 2)


if __name__ == "__main__":
    all_gpus = list(range(torch.cuda.device_count()))

    for gpu_combination in combinations(all_gpus, 2):
        src_id, dest_id = gpu_combination
        bandwidth = device_to_device_bandwidth_benchmark(src_id, dest_id)
        print(f"gpu {src_id} -> gpu {dest_id}: {bandwidth}")
