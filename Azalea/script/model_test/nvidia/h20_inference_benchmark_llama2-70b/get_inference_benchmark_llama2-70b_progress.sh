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

log_file=$1
task_docker="$2"
task_script="$3"

function is_task_still_running() {
    sudo docker ps 2> /dev/null |grep -w "$task_docker" &> /dev/null
    [[ $? -ne 0 ]] && { return 1; }
    sudo docker top "$task_docker" 2> /dev/null |grep "$task_script" &> /dev/null
    [[ $? -ne 0 ]] && { return 1; }
    return 0
}


if [[ ! -f "$log_file" ]]; then
    echo "exception:log file not found"
    exit 0
fi

log_content=$(cat "$log_file" 2> /dev/null)

echo "$log_content" | grep 'H20 inference benchmark task end failed' &> /dev/null
[[ $? -eq 0 ]] && { echo "exception:inference task end failed"; exit 0; }

echo "$log_content" | grep 'H20 inference benchmark task end success' &> /dev/null
[[ $? -eq 0 ]] && { echo 100; exit 0; }

is_task_still_running
[[ $? -ne 0 ]] && { echo "exception:task terminated abnormally"; exit 0; }

