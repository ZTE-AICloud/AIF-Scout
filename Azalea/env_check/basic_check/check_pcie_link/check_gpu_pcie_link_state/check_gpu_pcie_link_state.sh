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

vendor_id=$1
product_id=$2

pci_addrs=`lspci -nnn |grep -i $vendor_id:$product_id |awk '{print $1}'`
[[ -z $pci_addrs ]] && { echo "can not find pci info of gpu"; exit 1; }

echo "[InspectorRet Table]gpu pcie,speed,speed state,lane,lane state,result"
for pci_addr in $pci_addrs; do
    pcie_info=`sudo lspci -s $pci_addr -vvv`
    echo "$pcie_info"
    link_state=`echo "$pcie_info" | grep -i "LnkSta:"`
    read speed speed_state lane lane_state <<< $(echo "$link_state" | awk 'match($0, /Speed ([0-9]+GT\/s) \(([^)]+)\), Width (x[0-9]+) \(([^)]+)\)/, a) {print a[1], a[2], a[3], a[4]}')
    res="normal"
    if [[ $speed_state != "ok" || $lane_state != "ok" ]]; then
        res="abnormal"
    fi
    echo "[InspectorRet Table]$pci_addr,$speed,$speed_state,$lane,$lane_state,$res"
done
