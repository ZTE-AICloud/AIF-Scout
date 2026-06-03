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

function is_number() {
    local num=$1
    if [[ $num =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || [[ $num =~ ^-?\.[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

function get_nic_health_info_from_mlxlink() {
    tx_power=`echo "$health_info" |grep -i "^TX Power" |awk -F ":" '{print$NF}' |sed "s/ //g" |sed "s/,/ /g"`
    rx_power=`echo "$health_info" |grep -i "^RX Power" |awk -F ":" '{print$NF}' |sed "s/ //g" |sed "s/,/ /g"`
    tx_power=($tx_power)
    rx_power=($rx_power)
    tx_power_high_alarm=`echo "$health_info" |grep -i "^High alarm threshold" |awk '{print $(NF-1)}' |sed "s/,//g" |sed "s/dBm//g"`
    tx_power_low_alarm=`echo "$health_info" |grep -i "^Low alarm threshold" |awk '{print $(NF-1)}' |sed "s/,//g" |sed "s/dBm//g"`
    tx_power_high_warning=`echo "$health_info" |grep -i "^High warning threshold" |awk '{print $(NF-1)}' |sed "s/,//g" |sed "s/dBm//g"`
    tx_power_low_warning=`echo "$health_info" |grep -i "^Low warning threshold" |awk '{print $(NF-1)}' |sed "s/,//g" |sed "s/dBm//g"`
    rx_power_high_alarm=`echo "$health_info" |grep -i "^High alarm threshold" |awk '{print $(NF-2)}' |sed "s/,//g" |sed "s/dBm//g"`
    rx_power_low_alarm=`echo "$health_info" |grep -i "^Low alarm threshold" |awk '{print $(NF-2)}' |sed "s/,//g" |sed "s/dBm//g"`
    rx_power_high_warning=`echo "$health_info" |grep -i "^High warning threshold" |awk '{print $(NF-2)}' |sed "s/,//g" |sed "s/dBm//g"`
    rx_power_low_warning=`echo "$health_info" |grep -i "^Low warning threshold" |awk '{print $(NF-2)}' |sed "s/,//g" |sed "s/dBm//g"`

    temperature=`echo "$health_info" |grep -i "^Temperature" |awk -F ":" '{print$NF}' |sed "s/ //g"`
    temperature_high_alarm=`echo "$health_info" |grep -i "^High alarm threshold" |awk '{print $(NF-4)}' |sed "s/,//g" |sed "s/C//g"`
    temperature_low_alarm=`echo "$health_info" |grep -i "^Low alarm threshold" |awk '{print $(NF-4)}' |sed "s/,//g" |sed "s/C//g"`
    temperature_high_warning=`echo "$health_info" |grep -i "^High warning threshold" |awk '{print $(NF-4)}' |sed "s/,//g" |sed "s/C//g"`
    temperature_low_warning=`echo "$health_info" |grep -i "^Low warning threshold" |awk '{print $(NF-4)}' |sed "s/,//g" |sed "s/C//g"`
}

function get_nic_health_info_from_ethtool() {
    tx_power=`echo "$health_info" |grep -i "Transmit avg optical power" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g"`
    tx_power_channel=`echo "$health_info" |grep -i "Transmit avg optical power" |awk -F ":" '{print $1}' |awk -F'[()]' '{print $2}' |sed "s/ //g"`
    if [[ -z "$tx_power" ]]; then
        tx_power=`echo "$health_info" |grep -Ei "Laser output power[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g"`
        tx_power_channel=`echo "$health_info" |grep -Ei "Laser output power[[:space:]]+:" |awk -F ":" '{print $1}' |awk -F'[()]' '{print $2}' |sed "s/ //g"`
    fi
    rx_power=`echo "$health_info" |grep -i "Rcvr signal avg optical power" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g"`
    rx_power_channel=`echo "$health_info" |grep -i "Rcvr signal avg optical power" |awk -F ":" '{print $1}' |awk -F'[()]' '{print $2}' |sed "s/ //g"`
    if [[ -z "$rx_power" ]]; then
        rx_power=`echo "$health_info" |grep -Ei "Receiver signal average optical power[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g"`
        rx_power_channel=`echo "$health_info" |grep -Ei "Receiver signal average optical power[[:space:]]+:" |awk -F ":" '{print $1}' |awk -F'[()]' '{print $2}' |sed "s/ //g"`
    fi
    tx_power=($tx_power)
    tx_power_channel=($tx_power_channel)
    rx_power=($rx_power)
    rx_power_channel=($rx_power_channel)
    tx_power_high_alarm=`echo "$health_info" |grep -Ei "Laser output power high alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    tx_power_low_alarm=`echo "$health_info" |grep -Ei "Laser output power low alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    tx_power_high_warning=`echo "$health_info" |grep -Ei "Laser output power high warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    tx_power_low_warning=`echo "$health_info" |grep -Ei "Laser output power low warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    rx_power_high_alarm=`echo "$health_info" |grep -Ei "Laser rx power high alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    rx_power_low_alarm=`echo "$health_info" |grep -Ei "Laser rx power low alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    rx_power_high_warning=`echo "$health_info" |grep -Ei "Laser rx power high warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`
    rx_power_low_warning=`echo "$health_info" |grep -Ei "Laser rx power low warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $NF}' |sed "s/ //g" |sed "s/dBm//g"`

    temperature=`echo "$health_info" |grep -Ei "Module temperature[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $1}' |sed "s/ //g" |sed "s/degrees//g"`
    temperature_high_alarm=`echo "$health_info" |grep -Ei "Module temperature high alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $1}' |sed "s/ //g" |sed "s/degreesC//g"`
    temperature_low_alarm=`echo "$health_info" |grep -Ei "Module temperature low alarm threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $1}' |sed "s/ //g" |sed "s/degreesC//g"`
    temperature_high_warning=`echo "$health_info" |grep -Ei "Module temperature high warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $1}' |sed "s/ //g" |sed "s/degreesC//g"`
    temperature_low_warning=`echo "$health_info" |grep -Ei "Module temperature low warning threshold[[:space:]]+:" |awk -F ":" '{print $NF}' |awk -F "/" '{print $1}' |sed "s/ //g" |sed "s/degreesC//g"`
}

function get_nic_health_info() {
    local name=$1
    health_info=`sudo ethtool -m $name 2> /dev/null`
    echo "$health_info" |grep -qEi "power|temperature"
    if [[ $? -eq 0 ]]; then
        get_nic_health_info_from_ethtool
        return
    fi
    bus_info=`sudo ethtool -i "$name" 2> /dev/null |grep "bus-info:" |awk '{print $NF}'`
    if [[ -n "$bus_info" ]]; then
        health_info=`sudo mlxlink -d $bus_info --ddm --cable 2> /dev/null`
        echo "$health_info" |grep -qEi "power|temperature"
        if [[ $? -eq 0 ]]; then
            get_nic_health_info_from_mlxlink
            return
        fi
    fi
    health_info=""
}

function check_nic_health() {
    local nic_type=$1
    local name=$2
    echo "check $name nic"
    echo "[InspectorRet Title]$nic_type $name"
    get_nic_health_info $name
    if [[ -z "$health_info" ]]; then
        echo "nic name: $name can not find health info"
        echo "[InspectorRet Abnormal]can not find health info"
        return
    fi
    echo "$health_info"
    echo "[InspectorRet Table]item,value,result"
    length=${#tx_power[@]}
    for ((i=0; i<length; i++)); do
        power="${tx_power[i]}"
        channel="${tx_power_channel[i]}"
        item="tx power"
        [[ -n $channel ]] && { item="$item($channel)"; }
        level="normal"
        p=${power//dBm/}
        is_number $p
        if [[ $? -eq 0 ]]; then
            if [[ `echo $p $tx_power_high_alarm |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
                level="high alarm"
            else
                if [[ `echo $p $tx_power_high_warning |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
                    level="high warning"
                else
                    if [[ `echo $p $tx_power_low_alarm |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                        level="low alarm"
                    else
                        if [[ `echo $p $tx_power_low_warning |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                            level="low warning"
                        fi
                    fi
                fi
            fi
            if [[ $level == "normal" ]]; then
                echo "[InspectorRet Table]$item,$power($level),normal"
            else
                echo "[InspectorRet Table]$item,$power($level),abnormal"
            fi
        else
            echo "[InspectorRet Table]$item,$power,abnormal"
        fi
    done
    length=${#rx_power[@]}
    for ((i=0; i<length; i++)); do
        power="${rx_power[i]}"
        channel="${rx_power_channel[i]}"
        item="rx power"
        [[ -n $channel ]] && { item="$item($channel)"; }
        level="normal"
        p=${power//dBm/}
        is_number $p
        if [[ $? -eq 0 ]]; then
            if [[ `echo $p $rx_power_high_alarm |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
                level="high alarm"
            else
                if [[ `echo $p $rx_power_high_warning |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
                    level="high warning"
                else
                    if [[ `echo $p $rx_power_low_alarm |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                        level="low alarm"
                    else
                        if [[ `echo $p $rx_power_low_warning |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                            level="low warning"
                        fi
                    fi
                fi
            fi
            if [[ $level == "normal" ]]; then
                echo "[InspectorRet Table]$item,$power($level),normal"
            else
                echo "[InspectorRet Table]$item,$power($level),abnormal"
            fi
        else
            echo "[InspectorRet Table]$item,$power,abnormal"
        fi
    done

    level="normal"
    t=${temperature//C/}
    is_number $t
    if [[ $? -eq 0 ]]; then
        if [[ `echo $t $temperature_high_alarm |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
            level="high alarm"
        else
            if [[ `echo $t $temperature_high_warning |awk '{if ($1>$2) print(1)}'` == 1 ]]; then
                level="high warning"
            else
                if [[ `echo $t $temperature_low_alarm |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                    level="low alarm"
                else
                    if [[ `echo $t $temperature_low_warning |awk '{if ($1<$2) print(1)}'` == 1 ]]; then
                        level="low warning"
                    fi
                fi
            fi
        fi
        if [[ $level == "normal" ]]; then
            echo "[InspectorRet Table]temperature,$temperature($level),normal"
        else
            echo "[InspectorRet Table]temperature,$temperature($level),abnormal"
        fi
    else
        echo "[InspectorRet Table]temperature,$temperature,abnormal"
    fi
}

function check_param_optical_module_health() {
    echo "check parameter optical module health"
    for nic_name in $param_nic; do
        check_nic_health "parameter nic" $nic_name
    done
}

function check_storage_optical_module_health() {
    echo "check storage optical module health"
    for nic_name in $stor_nic; do
        check_nic_health "storage nic" $nic_name
    done
}

if [[ -n $param_nic && $param_nic != "None" ]]; then
    check_param_optical_module_health
fi

if [[ -n $stor_nic && $stor_nic != "None" ]]; then
    check_storage_optical_module_health
fi
