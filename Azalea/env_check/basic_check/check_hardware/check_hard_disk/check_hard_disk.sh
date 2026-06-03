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

function check_hard_disk() {
    info=`lsblk -o "KNAME,TYPE,SIZE,MODEL" |grep -E "sd[a-z]|nvme" |grep disk`
    model_show=`echo "$info" |awk '{for(i=4; i<=NF; i++) printf "%s ", $i; print ""}' |sort |uniq |sed 's/[[:space:]]\+$//' |tr '\n' ','`
    model_show=$(echo "$model_show" | awk '{sub(/,$/, ""); print}')
    echo "[InspectorRet]Hard disk model: $model_show"

    total=`echo "$info" |awk '{print $3}'`
    count=0
    for t in $total; do
        echo $t |grep -i "T" &> /dev/null
        if [[ $? -eq 0 ]]; then
            t=${t//T/}
            count=`echo $t $count |awk '{printf($1*1024+$2)}'`
        else
            echo $t |grep -i "G" &> /dev/null
            if [[ $? -eq 0 ]]; then
                t=${t//G/}
                count=`echo $t $count |awk '{printf($1+$2)}'`
            fi
        fi
    done
    echo "[InspectorRet]Hard disk total: $count GB"
}

check_hard_disk
