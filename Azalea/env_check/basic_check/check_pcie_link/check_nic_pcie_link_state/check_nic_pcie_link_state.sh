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

function check_param_nic_state {
    for nic in $param_nic; do
        pci_addr=$(sudo ethtool -i "$nic" 2>/dev/null | grep bus-info: | awk '{print $NF}')
        if [[ -z $pci_addr ]];then
            echo "[InspectorRet Table]$nic,parameter nic,-,-,-,-,abnormal"
        else
            pcie_info=`sudo lspci -s $pci_addr -vvv`
            echo -e "$nic pcie info:\n$pcie_info"
            link_state=`echo "$pcie_info" | grep -i "LnkSta:"`
            read speed speed_state lane lane_state <<< $(echo "$link_state" | awk 'match($0, /Speed ([0-9]+GT\/s) \(([^)]+)\), Width (x[0-9]+) \(([^)]+)\)/, a) {print a[1], a[2], a[3], a[4]}')
            res="normal"
            if [[ $speed_state != "ok" || $lane_state != "ok" ]]; then
                res="abnormal"
            fi
            echo "[InspectorRet Table]$nic,parameter nic,$speed,$speed_state,$lane,$lane_state,$res"
        fi
    done
}

function check_stor_nic_state {
    for nic in $stor_nic; do
        pci_addr=$(sudo ethtool -i "$nic" 2>/dev/null | grep bus-info: | awk '{print $NF}')
        if [[ -z $pci_addr ]];then
            echo "[InspectorRet Table]$nic,storage nic,-,-,-,-,abnormal"
        else
            pcie_info=`sudo lspci -s $pci_addr -vvv`
            echo -e "$nic pcie info:\n$pcie_info"
            link_state=`echo "$pcie_info" | grep -i "LnkSta:"`
            read speed speed_state lane lane_state <<< $(echo "$link_state" | awk 'match($0, /Speed ([0-9]+GT\/s) \(([^)]+)\), Width (x[0-9]+) \(([^)]+)\)/, a) {print a[1], a[2], a[3], a[4]}')
            res="normal"
            if [[ $speed_state != "ok" || $lane_state != "ok" ]]; then
                res="abnormal"
            fi
            echo "[InspectorRet Table]$nic,storage nic,$speed,$speed_state,$lane,$lane_state,$res"
        fi
    done
}

echo "[InspectorRet Table]nic name,type,speed,speed state,lane,lane state,result"
if [[ -n $param_nic && $param_nic != "None" ]]; then
    check_param_nic_state
fi

if [[ -n $stor_nic && $stor_nic != "None" ]]; then
    check_stor_nic_state
fi
