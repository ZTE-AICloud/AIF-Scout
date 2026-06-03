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

if [ -z "$1" ]; then
    echo "Error: Please provide the check type as an argument. Support check type: INT8, BF16, TF32, FP32"
    exit 1
fi

check_type=$1

gpu_array=$(nvidia-smi topo -m 2>/dev/null | head -n 1 | grep -o 'GPU[0-9]\+' | grep -o '[0-9]\+')

for gpu_id in $gpu_array; do
    python /workspace/tools/tflops.py "$check_type" "$gpu_id" | tail -n 1 | awk -v gpu_id="$gpu_id" '{print "gpu "gpu_id": "$NF}' &
done
wait
