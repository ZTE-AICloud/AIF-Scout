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

test_dir=$1
block_size=$2
block_count=$3
host_ip=$4

df -hT | grep -wq $test_dir
if [[ $? -ne 0 ]]; then
    echo "$test_dir is not mounted"
    exit 1
fi

test_file="$test_dir/ait_bandwidth_$host_ip.txt"
sudo rm -rf $test_file
test_res=`dd if=/dev/zero of=${test_file} bs=$block_size count=$block_count 2>&1`
echo "$test_res"
data=`echo "$test_res" |grep -i copied |awk -F '[()]' '{print $2}' |awk -F ',' '{print $1}'`
time=`echo "$test_res" |grep -i copied |awk -F "," '{print $(NF-1)}'`
bandwidth=`echo "$test_res" |grep -i copied |awk -F "," '{print $NF}'`
echo "[InspectorRet]$data,$time,$bandwidth"
sudo rm -rf $test_file
