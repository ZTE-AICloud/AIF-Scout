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

target_addrs=$1
packet_size=$2
packet_count=$3
egress_interface=$4

target_addrs=$(echo "$target_addrs" |sed 's/,/ /g')
egress_interface=$(echo "$egress_interface" |sed 's/,/ /g')

param="-q"
if [[ -n "$packet_size" && $packet_size != "None" ]]; then
    param="$param -s $packet_size"
fi
if [[ -n "$packet_count" && $packet_count != "None" ]]; then
    param="$param -c $packet_count"
else
    param="$param -c 3"
fi

function get_nic_ip_addr() {
    local nic=$1
    local ip_addr_info=`ip addr show $nic 2>/dev/null`
    nic_addr=`echo "$ip_addr_info" |grep -w "inet" |head -n 1 |awk '{print $2}' |awk -F '/' '{print $1}'`
    if [[ -n $nic_addr ]]; then
        return
    fi
    nic_addr=`echo "$ip_addr_info" |grep -w "inet6" | grep -Ev "[[:space:]]fe80" |head -n 1 |awk '{print $2}' |awk -F '/' '{print $1}'`
}

function ping_check() {
    local ping_param=$*
    ping_res=`ping $ping_param`
    loss_info=`echo "$ping_res" |grep "packet loss"`
    transmitted=`echo $loss_info |awk -F ',' '{print $1}' |awk '{print $1}'`
    received=`echo $loss_info |awk -F ',' '{print $2}' |awk '{print $1}'`
    loss=`echo $loss_info |awk -F ',' '{print $(NF-1)}' |awk '{print $1}'`
    rtt_info=`echo "$ping_res" |grep rtt |awk -F '=' '{print $NF}'`
    if [[ $loss == "0%" ]]; then
        res="normal"
    else
        res="abnormal"
    fi
}

if [[ -n "$egress_interface" && $egress_interface != "None" ]]; then
    echo "[InspectorRet Table]egress_interface,address,transmitted,received,loss packet,rtt(min/avg/max/mdev),result"
    for interface in $egress_interface; do
        get_nic_ip_addr $interface
        if [[ -z $nic_addr ]]; then
            echo "the ip address of $interface not found"
            echo "[InspectorRet Table]$interface(ip address not found),,,,,,abnormal"
            break
        fi
        for addr in $target_addrs; do
            ping_check $param -I $nic_addr $addr
            echo -e "ping $addr from $interface($nic_addr) result:\n$ping_res"
            echo "[InspectorRet Table]$interface($nic_addr),$addr,$transmitted,$received,$loss,$rtt_info,$res"
        done
    done
else
    echo "[InspectorRet Table]address,transmitted,received,loss packet,rtt(min/avg/max/mdev),result"
    for addr in $target_addrs; do
        ping_check $param $addr
        echo -e "ping $addr result:\n$ping_res"
        echo "[InspectorRet Table]$addr,$transmitted,$received,$loss,$rtt_info,$res"
    done
fi
