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
stor_nic=$2
gid_index=${3-3}
packet_size=${4-1073741824}
packet_count=${5-10}
server_ip=$6
client_ip=$7
client_user=$8
client_pwd=$9
client_port=${10}
stor_nic=$(echo "$stor_nic" |sed 's/,/ /g')
ssh_param="-p ${client_pwd} ssh -o StrictHostKeyChecking=no -p ${client_port} ${client_user}@${client_ip}"
timeout=1000
echo "sever ip: $server_ip, client ip: $client_ip"

function is_number() {
    local num=$1
    if [[ $num =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || [[ $num =~ ^-?\.[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

function ssh_exec() {
    local ssh_cmd=$*
    sshpass $ssh_param "${ssh_cmd}" < /dev/null
}

function kill_ib_write() {
    pkill -9 -f ib_write_bw &> /dev/null
    ssh_exec pkill -9 -f ib_write_bw &> /dev/null
    return 0
}

function get_ip_link_info() {
    server_nic_link_info=`ip link show`
    client_nic_link_info=`ssh_exec ip link show`
    if [[ -z $server_nic_link_info ]]; then
        echo "ip link info is empty on $server_ip"
        exit 1
    fi
    if [[ -z $client_nic_link_info ]]; then
        echo "ip link info is empty on $server_ip"
        exit 1
    fi
}

function get_rdma_link_info() {
    server_rdma_link_info=`rdma link`
    client_rdma_link_info=`ssh_exec rdma link`
    if [[ -z $server_rdma_link_info ]]; then
        echo "rdma link info is empty on $server_ip"
        exit 1
    fi
    if [[ -z $client_rdma_link_info ]]; then
        echo "rdma link info is empty on $server_ip"
        exit 1
    fi
}

function get_stor_bond_info() {
    nic_count=`echo $stor_nic |wc -w`
    if [[ $nic_count == 1 ]]; then
        server_nic=`echo "$server_nic_link_info" |grep -w $stor_nic: |grep -o 'master [^ ]*' |awk '{print $NF}'`
        if [[ -z $server_nic ]]; then
            server_nic=$stor_nic
        fi
        client_nic=`echo "$client_nic_link_info" |grep -w $stor_nic: |grep -o 'master [^ ]*' |awk '{print $NF}'`
        if [[ -z $client_nic ]]; then
            client_nic=$stor_nic
        fi
    else
        server_nic=""
        client_nic=""
        for nic in $stor_nic; do
            server_bond=`echo "$server_nic_link_info" |grep -w $nic: |grep -o 'master [^ ]*' |awk '{print $NF}'`
            if [[ -z $server_bond ]]; then
                echo "can not find storage bond of $nic on $server_ip"
                exit 1
            fi
            server_nic="$server_nic $server_bond"
            client_bond=`echo "$client_nic_link_info" |grep -w $nic: |grep -o 'master [^ ]*' |awk '{print $NF}'`
            if [[ -z $client_bond ]]; then
                echo "can not find storage bond of $nic on $client_ip"
                exit 1
            fi
            client_nic="$client_nic $client_bond"
        done
        server_nic=`echo $server_nic |tr ' ' '\n' |sort -u`
        server_nic_count=`echo $server_nic |wc -l`
        if [[ $server_nic_count != 1 ]]; then
            echo "the bond of storage nic is inconsistent on $server_ip"
            exit 1
        fi
        client_nic=`echo $client_nic |tr ' ' '\n' |sort -u`
        client_nic_count=`echo $client_nic |wc -l`
        if [[ $client_nic_count != 1 ]]; then
            echo "the bond of storage nic is inconsistent on $client_ip"
            exit 1
        fi
    fi
    server_rdma_dev_name=`echo "$server_rdma_link_info" |grep -w $server_nic |awk '{print $2}' |cut -d '/' -f1`
    if [[ -z $server_rdma_dev_name ]]; then
        for nic in $stor_nic; do
            server_rdma_dev_name=`echo "$server_rdma_link_info" |grep -w $nic |awk '{print $2}' |cut -d '/' -f1`
            if [[ -n $server_rdma_dev_name ]]; then
                break
            fi
        done
    fi
    [[ -z $server_rdma_dev_name ]] && { echo "can not find the rdma dev name of $server_nic on $server_ip"; exit 1; }
    echo "$server_ip rdma dev name: $server_rdma_dev_name"
    client_rdma_dev_name=`echo "$client_rdma_link_info" |grep -w $client_nic |awk '{print $2}' |cut -d '/' -f1`
    if [[ -z $client_rdma_dev_name ]]; then
        for nic in $stor_nic; do
            client_rdma_dev_name=`echo "$client_rdma_link_info" |grep -w $nic |awk '{print $2}' |cut -d '/' -f1`
            if [[ -n $client_rdma_dev_name ]]; then
                break
            fi
        done
    fi
    [[ -z $client_rdma_dev_name ]] && { echo "can not find the rdma dev name of $client_nic on $client_ip"; exit 1; }
    echo "$client_ip rdma dev name: $client_rdma_dev_name"
}

function nic_ib_write() {
    echo "begin to ib write"
    for ((j=0;j<$packet_count;j++ )); do
        kill_ib_write
        ib_write_bw -d "$server_rdma_dev_name" -x "$gid_index" -F --report_gbits -s "$packet_size" &> /dev/null &
        sleep 3
        ssh_exec timeout $timeout ib_write_bw -d "$client_rdma_dev_name" -x "$gid_index" -F --report_gbits -s "$packet_size" "$server_ip" &> /dev/null
        if [[ $? -ne 0 ]]; then
            kill_ib_write
            echo "ib write failed"
            exit 1
        fi
    done
    echo "ib write finish"
    kill_ib_write
    ib_write_bw -d "$server_rdma_dev_name" -x "$gid_index" -F --report_gbits -s "$packet_size" &> /dev/null &
    sleep 3
    ssh_exec ib_write_bw -d "$client_rdma_dev_name" -x "$gid_index" -F --report_gbits -s "$packet_size" "$server_ip" &> /dev/null &
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
    local type=$1
    local name=$2

    if [[ "$type" == "remote" ]]; then
        health_info=`ssh_exec sudo ethtool -m $name 2> /dev/null`
        echo "$health_info" |grep -qEi "power|temperature"
        if [[ $? -eq 0 ]]; then
            get_nic_health_info_from_ethtool
            return
        fi
        bus_info=`ssh_exec sudo ethtool -i "$name" 2> /dev/null |grep "bus-info:" |awk '{print $NF}'`
        if [[ -n "$bus_info" ]]; then
            health_info=`ssh_exec $client_info sudo mlxlink -d $bus_info --ddm --cable 2> /dev/null`
            echo "$health_info" |grep -qEi "power|temperature"
            if [[ $? -eq 0 ]]; then
                get_nic_health_info_from_mlxlink
                return
            fi
        fi
    else
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
    fi
    health_info=""
}

function check_nic_health() {
    local type=$1
    local name=$2
    local host=$server_ip
    if [[ $type == "remote" ]]; then
        host=$client_ip
    fi
    echo "$host:check $name nic health after stress test between $server_ip and $client_ip"
    echo "$host:[InspectorRet Title]check nic $name health after stress test between $server_ip and $client_ip"
    get_nic_health_info $type $name
    if [[ -z "$health_info" ]]; then
        echo "$host:nic name: $name can not find health info"
        echo "$host:[InspectorRet Abnormal]nic name: $name can not find health info"
        return
    fi
    echo "$health_info" |sed "s/^/$host:/"
    echo "$host:[InspectorRet Table]item,value,result"
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
                echo "$host:[InspectorRet Table]$item,$power($level),normal"
            else
                echo "$host:[InspectorRet Table]$item,$power($level),abnormal"
            fi
        else
            echo "$host:[InspectorRet Table]$item,$power,abnormal"
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
                echo "$host:[InspectorRet Table]$item,$power($level),normal"
            else
                echo "$host:[InspectorRet Table]$item,$power($level),abnormal"
            fi
        else
            echo "$host:[InspectorRet Table]$item,$power,abnormal"
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
            echo "$host:[InspectorRet Table]temperature,$temperature($level),normal"
        else
            echo "$host:[InspectorRet Table]temperature,$temperature($level),abnormal"
        fi
    else
        echo "$host:[InspectorRet Table]temperature,$temperature,abnormal"
    fi
}

if [[ $operation == 'execute' ]]; then
    which sshpass &> /dev/null
    if [[ $? -ne 0 ]]; then
        echo "sshpass not installed"
        exit 1
    fi
    get_ip_link_info
    get_rdma_link_info
    get_stor_bond_info
    nic_ib_write
    for nic in $stor_nic; do
        check_nic_health "local" $nic
        check_nic_health "remote" $nic
    done
    kill_ib_write
elif [[ $operation == 'stop' ]]; then
    sudo pkill -2 -f "storage_nic_stress.sh execute"
    kill_ib_write
fi
