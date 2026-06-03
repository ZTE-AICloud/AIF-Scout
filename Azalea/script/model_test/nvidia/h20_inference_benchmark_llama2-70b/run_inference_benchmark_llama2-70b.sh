#!/bin/bash
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

LOG_FILE=${1:-"performance_test.log"}
task_name=${2:-"h20_benchmark"}
max_batch_size=${3:-"64"}
max_input_len=${4:-"512"}
max_output_len=${5:-"512"}
tp_size=${6:-"8"}

mpirun -n $tp_size --allow-run-as-root \
    python3 /workspace/TensorRT-LLM/benchmarks/python/benchmark.py \
    -m llama_70b \
    --mode plugin \
    --warm_up 1 \
    --dtype bfloat16 \
    --quantization fp8 \
    --batch_size ${max_batch_size} \
    --max_batch_size ${max_batch_size} \
    --input_output_len "${max_input_len},${max_output_len}" \
    --max_output_len ${max_output_len} \
    --duration 0 \
    --num_runs 5 \
    --log_level info >> $LOG_FILE 2>&1

if [[ $? -eq 0 ]]; then
    echo "H20 inference benchmark task end success" >> $LOG_FILE
    exit 0
else
    echo "H20 inference benchmark task end failed" >> $LOG_FILE
    exit 1
fi
