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

function check_memory() {
    m=`sudo dmidecode -t memory | grep 'Manufacturer:' |awk -F "Manufacturer:" '{print $NF}' |sort |uniq`
    m=`echo $m`
    echo "[InspectorRet]Memory model: $m"

    t=0
    info=`sudo dmidecode -t memory | grep -E "^[[:space:]]+Size:" |awk '{print $2}'`
    for i in $info; do
        t=`echo $t $i |awk '{printf($1+$2)}'`
    done
    echo "[InspectorRet]Total memory: $t GB"
}

check_memory
