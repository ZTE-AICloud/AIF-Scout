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

operation=$1
param_nic=$2
gid_index=${3-3}
packet_size=${4-1073741824}
packet_count=${5-10}
server_ip=$6

timeout=1000

param_nic=$(echo "$param_nic" |sed 's/,/ /g')
nic_list=($param_nic)

function is_number() {
    local num=$1
    if [[ $num =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || [[ $num =~ ^-?\.[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

function kill_ib_write() {
    pkill -9 -f ib_write_bw &> /dev/null
    return 0
}

function get_rdma_dev_name() {
    nic=$1
    dev_name=`rdma link 2> /dev/null |grep -w $nic |awk '{print $2}' |cut -d'/' -f1`
    echo $dev_name
}

function nic_stress_test() {
    nic_length=${#nic_list[@]}
    [[ "$nic_length" == 0 ]] && { echo "nic cannot find"; exit 1; }
    for ((nic_i=0; nic_i<nic_length; nic_i=nic_i+2)); do
        nic_server="${nic_list[nic_i]}"
        nic_client="${nic_list[((nic_i+1))]}"
        if [[ -z "$nic_client" ]]; then
            echo "[InspectorRet Abnormal]the count of nic cards is not even, $nic_server cannot to check"
            continue
        fi
        nic_ib_write $nic_server $nic_client
        if [[ $? -ne 0 ]]; then
            continue
        fi
        check_nic_health "$nic_server"
        check_nic_health "$nic_client"
        kill_ib_write
    done
}

function nic_ib_write() {
    nic_server=$1
    nic_client=$2
    rdma_server=`get_rdma_dev_name $nic_server`
    if [[ -z $rdma_server ]]; then
        echo "[InspectorRet Abnormal]can not find the rdma dev name of $nic_server"
        return 1
    fi
    rdma_client=`get_rdma_dev_name $nic_client`
    if [[ -z $rdma_client ]]; then
        echo "[InspectorRet Abnormal]can not find the rdma dev name of $nic_client"
        return 1
    fi
    echo "$nic_server & $nic_client: begin to ib write"
    for ((j=0;j<$packet_count;j++ )); do
        kill_ib_write
        ib_write_bw -d "$rdma_server" -x "$gid_index" -F --report_gbits -s "$packet_size" &> /dev/null &
        sleep 3
        timeout $timeout ib_write_bw -d "$rdma_client" -x "$gid_index" -F --report_gbits -s "$packet_size" "$server_ip" &> /dev/null
        if [[ $? -ne 0 ]]; then
            kill_ib_write
            echo "[InspectorRet Abnormal]$nic_server & $nic_client: ib write failed"
            return 1
        fi
    done
    echo "$nic_server & $nic_client: ib write finish"
    kill_ib_write
    ib_write_bw -d "$rdma_server" -x "$gid_index" -F --report_gbits -s "$packet_size" &> /dev/null &
    sleep 3
    ib_write_bw -d "$rdma_client" -x "$gid_index" -F --report_gbits -s "$packet_size" "$server_ip" &> /dev/null &
    sleep 10
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
    local name=$1
    echo "check $name nic health after stress test"
    echo "[InspectorRet Title]check nic $name health after stress test"
    get_nic_health_info $name
    if [[ -z "$health_info" ]]; then
        echo "nic name: $name can not find health info"
        echo "[InspectorRet Abnormal]nic name: $name can not find health info"
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

if [[ $operation == 'execute' ]]; then
    nic_stress_test
elif [[ $operation == 'stop' ]]; then
    sudo pkill -2 -f "parameter_nic_stress.sh execute"
    kill_ib_write
fi
