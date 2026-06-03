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
gid_index=$2

param_nic=$(echo "$param_nic" |sed 's/,/ /g')
gid_infos=`show_gids`
echo "$gid_infos"

function is_dinghai_nic() {
    nic=$1
    ethtool -i $nic |grep -i driver |grep -qi dinghai
    if [[ $? -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

function get_rdma_dev_name() {
    nic=$1
    dev_name=`rdma link 2> /dev/null |grep -w $nic |awk '{print $2}' |cut -d'/' -f1`
    echo $dev_name
}

function check_dinghai_config() {
    local nic=$1
    echo "$nic is dinghai nic"
    pfc_info=`dcb pfc show dev $nic prio-pfc`
    echo "nic pfc info: $pfc_info"
    echo $pfc_info |grep -qwi off
    if [[ $? -eq 0 ]]; then
        pfc_res="abnormal"
    else
        echo $pfc_info |grep -qwi on
        if [[ $? -eq 0 ]]; then
            pfc_res="normal"
        else
            pfc_res="abnormal"
        fi
    fi
    echo "[InspectorRet Table]pfc,$pfc_info,$pfc_res"

    rdma_dev_name=`get_rdma_dev_name $nic`
    if [[ -z $rdma_dev_name ]]; then
        return
    fi
    tos=`sudo zxdh_cma_roce_tos -d $rdma_dev_name`
    echo "nic tos info: $tos"
    if [[ $tos == 106 ]]; then
        echo "[InspectorRet Table]tos,$tos,normal"
    else
        echo "[InspectorRet Table]tos,$tos(expected 106),abnormal"
    fi
    gid=$(echo "$gid_infos" |grep -wi v2 |grep -w $rdma_dev_name |grep -Ev "[[:space:]]fe80" |awk '{print $3}')
    echo "nic gid: $gid"
    if [[ $gid == $gid_index ]]; then
        gid_res="normal"
    else
        gid_res="abnormal"
    fi
    if [[ $gid == $gid_index ]]; then
        echo "[InspectorRet Table]gid index,$gid,normal"
    else
        echo "[InspectorRet Table]gid index,$gid(expected $gid_index),abnormal"
    fi
}

function check_mlx_config() {
    local nic=$1
    echo "$nic is mlx nic"
    roce_conf=$(sudo mlnx_qos -i $nic)
    echo "$roce_conf"
    trust_state=$(echo "$roce_conf" |grep -i "Priority trust state" |awk '{print $NF}')
    if [[ $trust_state == "dscp" ]]; then
        echo "[InspectorRet Table]Priority trust state,$trust_state,normal"
    else
        echo "[InspectorRet Table]Priority trust state,$trust_state(expected dscp),abnormal"
    fi
    pfc_conf=$(echo "$roce_conf" |awk '/PFC configuration:/{n=1} n==1 {print;}' |sed -n '/priority/{:a;N;/buffer/!ba;p}')
    pfc_priority=`echo "$pfc_conf" |grep "priority" |awk '{for(i=2;i<=NF;i++) printf("%s%s", $i, (i==NF?"":" "))}'`
    pfc_enabled=`echo "$pfc_conf" |grep "enabled" |awk '{for(i=2;i<=NF;i++) printf("%s%s", $i, (i==NF?"":" "))}'`
    pfc_buffer=`echo "$pfc_conf" |grep "buffer" |awk '{for(i=2;i<=NF;i++) printf("%s%s", $i, (i==NF?"":" "))}'`
    if [[ $pfc_priority == "0 1 2 3 4 5 6 7" ]]; then
        echo "[InspectorRet Table]PFC priority,$pfc_priority,normal"
    else
        echo "[InspectorRet Table]PFC priority,$pfc_priority(expected 0 1 2 3 4 5 6 7),abnormal"
    fi
    if [[ $pfc_enabled == "0 0 0 1 1 0 0 0" ]]; then
        echo "[InspectorRet Table]PFC enabled,$pfc_enabled,normal"
    else
        echo "[InspectorRet Table]PFC enabled,$pfc_enabled(expected  0 0 0 1 1 0 0 0 ),abnormal"
    fi
    if [[ $pfc_buffer == "0 0 0 1 1 0 0 0" ]]; then
        echo "[InspectorRet Table]PFC buffer,$pfc_buffer,normal"
    else
        echo "[InspectorRet Table]PFC buffer,$pfc_buffer(expected  0 0 0 1 1 0 0 0 ),abnormal"
    fi

    rdma_dev_name=`get_rdma_dev_name $nic`
    if [[ -z $rdma_dev_name ]]; then
        return
    fi
    traffic_class=`sudo cat /sys/class/infiniband/$rdma_dev_name/tc/1/traffic_class 2> /dev/null |awk -F "=" '{print $NF}'`
    echo "nic traffic class: $traffic_class"
    if [[ $traffic_class == 106 ]]; then
        echo "[InspectorRet Table]traffic class,$traffic_class,normal"
    else
        echo "[InspectorRet Table]traffic class,$traffic_class(expected 106),abnormal"
    fi
    tos=`sudo cma_roce_tos -d $rdma_dev_name`
    echo "nic tos info: $tos"
    if [[ $tos == 106 ]]; then
        echo "[InspectorRet Table]tos,$tos,normal"
    else
        echo "[InspectorRet Table]tos,$tos(expected 106),abnormal"
    fi
    gid=$(echo "$gid_infos" |grep -wi v2 |grep -w $rdma_dev_name |grep -Ev "[[:space:]]fe80" |awk '{print $3}')
    echo "nic gid: $gid"
    if [[ $gid == $gid_index ]]; then
        gid_res="normal"
    else
        gid_res="abnormal"
    fi
    if [[ $gid == $gid_index ]]; then
        echo "[InspectorRet Table]gid index,$gid,normal"
    else
        echo "[InspectorRet Table]gid index,$gid(expected $gid_index),abnormal"
    fi
}

function check_param_nic_config() {
    echo "check parameter nic"
    for nic in $param_nic; do
        echo "[InspectorRet Title]parameter nic $nic"
        echo "[InspectorRet Table]item,value,result"
        is_dinghai_nic $nic
        if [[ $? -eq 0 ]]; then
            check_dinghai_config $nic
        else
            check_mlx_config $nic
        fi
    done
}

check_param_nic_config
