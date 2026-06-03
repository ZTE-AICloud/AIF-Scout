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

function check_cpu() {
    cpu_info=`lscpu`
    m=`echo "$cpu_info" |grep -i '^Model name:' |awk -F "Model name:" '{print $NF}'`
    m=`echo $m`
    echo "[InspectorRet]CPU model name: $m"

    n=`echo "$cpu_info" |grep -i '^CPU(s):' |awk -F ":" '{print $NF}'`
    n=`echo $n`
    echo "[InspectorRet]CPU count: $n"
}

check_cpu
