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

import os
import fire


def main(dtype: str, device_id: int):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(device_id)

    import torch
    import triton
    import triton.ops

    if not torch.cuda.is_available():
        print(f"Invalid device ID: {device_id}.")
        exit(1)
    device = torch.device("cuda")
    if dtype.upper() == "FP32":
        torch.backends.cuda.matmul.allow_tf32 = False
    else:
        torch.backends.cuda.matmul.allow_tf32 = True

    dtype_mapping = {
        "BF16": torch.bfloat16,
        "INT8": torch.int8,
        "TF32": torch.float32,  # TF32 在 PyTorch 中通常被视为 FP32
        "FP32": torch.float32,
        "FP16": torch.float16,
    }

    # 获取对应的 PyTorch 类型
    mapped_dtype = dtype_mapping.get(dtype.upper())

    if not mapped_dtype:
        print(
            f"Unsupported data type: '{dtype}'. Supported types are: {', '.join(dtype_mapping.keys())}"
        )
        exit(1)

    stream = torch.cuda.Stream()
    torch.cuda.set_stream(stream)
    matmul_tflops = {}
    for M in [4096, 8192]:
        for K in [8192]:
            for N in [4096]:
                torch.manual_seed(0)
                if mapped_dtype == torch.int8:
                    a = torch.randint(-128, 127, (M, K),
                                      dtype=mapped_dtype, device=device)
                    b = torch.randint(-128, 127, (N, K),
                                      dtype=mapped_dtype, device=device)
                    b = b.t()  # only test row-col layout
                else:
                    a = (torch.randn(M, K, device=device)
                         * 127).to(dtype=mapped_dtype)
                    b = (torch.randn(K, N, device=device)
                         * 127).to(dtype=mapped_dtype)

                fn = lambda: triton.ops.matmul(a, b)
                if mapped_dtype == torch.float32:
                    fn = lambda: torch.matmul(a, b)
                ms = triton.testing.do_bench_cudagraph(fn)
                matmul_tflops[f"m={M},k={K},n={N}"] = round(
                    2 * M * N * K / ms / 1e9, 2)
                del a, b

    for key, value in matmul_tflops.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    fire.Fire(main)
