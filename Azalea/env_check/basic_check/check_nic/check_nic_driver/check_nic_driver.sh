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

param_nic=$1
stor_nic=$2

param_nic=$(echo "$param_nic" |sed 's/,/ /g')
stor_nic=$(echo "$stor_nic" |sed 's/,/ /g')

function check_param_nic_driver() {
    echo "check parameter nic"
    for nic in $param_nic; do
        driver=`ethtool -i $nic |grep "^driver:" |awk '{print $NF}'`
        version=`ethtool -i $nic |grep "^version:" |awk '{print $NF}'`
        echo "[InspectorRet Param]$nic:$driver-$version"
    done
}

function check_stor_nic_driver() {
    echo "check storage nic"
    for nic in $stor_nic; do
        driver=`ethtool -i $nic |grep "^driver:" |awk '{print $NF}'`
        version=`ethtool -i $nic |grep "^version:" |awk '{print $NF}'`
        echo "[InspectorRet Stor]$nic:$driver-$version"
    done
}

if [[ -n $param_nic && $param_nic != "None" ]]; then
    check_param_nic_driver
fi

if [[ -n $stor_nic && $stor_nic != "None" ]]; then
    check_stor_nic_driver
fi
