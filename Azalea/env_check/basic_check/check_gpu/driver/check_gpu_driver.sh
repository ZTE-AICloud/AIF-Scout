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

gpu_manufacturer=$1

function check_nvidia_gpu_driver() {
    which nvidia-smi &> /dev/null
    if [[ $? -eq 0 ]]; then
        gpu_driver=`nvidia-smi --query-gpu=driver_version --format=csv |grep -v driver_version |sort |uniq`
    else
        gpu_driver=`sudo chroot /paasdata/op-data/nvidia-driver/driver bash -c "nvidia-smi --query-gpu=driver_version --format=csv |grep -v driver_version |sort |uniq"`
    fi
    echo "[InspectorRet]GPU driver: $gpu_driver"
}

echo "Check $gpu_manufacturer gpu driver"
if [[ "$gpu_manufacturer" == "NVIDIA" ]]; then
    check_nvidia_gpu_driver
else
    echo "Unknown gpu manufacturer:$gpu_manufacturer"
    exit 1
fi
