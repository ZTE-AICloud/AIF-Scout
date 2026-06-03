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

# only support 2 nodes
# spending time calculation
# 2 nodes exec EXEC_TIME
# when ssh_interval=0.1 EXEC_TIME = 20s

which sshpass &> /dev/null
if [ $? -ne 0 ]; then
    echo "sshpass not installed"
    exit 1
fi

help=0
# Get args.
while getopts ":h:u:p:P:t:d:g:" opt; do
    case $opt in
        h) input_hosts=$OPTARG ;;
        u) input_users=$OPTARG ;;
        p) input_ports=$OPTARG ;;
        P) input_passwds=$OPTARG ;;
        d) input_network_devices=$OPTARG ;;
        g) input_gid=$OPTARG ;;
        t) input_timeout=$OPTARG ;;
        \?) echo "Invalid option -$OPTARG" >&2; help=1 ;;
    esac
done

if [ $help -eq 1 ]; then
  echo "h) host name or ip"
  echo "u) user name"
  echo "p) port"
  echo "P) password"
  echo "d) RoCE network devices"
  echo "g) RoCE gid"
  echo "t) timeout ssh exec"
  echo "H) help"
  exit 1
fi

# Set ip/host_name or port. 脚本执行节点不需要和检测节点互信了
NODES=$input_hosts # host1 host2
PORTS=$input_ports # port1 port2
USERS=$input_users # user1 user2
PASSWDS=$input_passwds # pwd1 pwd2
NETWORK_DEVICES=$input_network_devices # ens1 ens2 ens3 ...
GID=+$input_gid # default 3
TIME_OUT=$input_timeout # timeout ssh exec
if [ -z "$TIME_OUT" ]; then
    TIME_OUT=2
fi

IFS=' ' read -r node1 node2 <<< "$NODES"
IFS=' ' read -r port1 port2 <<< "$PORTS"
IFS=' ' read -r user1 user2 <<< "$USERS"
IFS=' ' read -r pwd1 pwd2 <<< "$PASSWDS"

# Necessary pause! otherwise ssh connection conflicts for single node check
# General >= 0.05，but cross check mlx device need >= 0.1.
ssh_interval=0.1
ib_info_cmd='info=`ibdev2netdev 2> /dev/null`; echo "$info"'

function ssh_exec
{
    args=("$@")
    host=$1
    port=$2
    user=$3
    passwd=$4

    ssh_cmd=${args[@]:4}

    if [ -z "$passwd" ]; then
        timeout $TIME_OUT ssh -p ${port} ${user}@${host} ${ssh_cmd}
        return 0
    fi
    # TIME_OUT<=1 时 server ib_send_lat 已结束 client还没起，之后起client 返回 1
    # 超时返回124；执行错误返回1；如果没有server，起client会立刻产生错误返回1
    timeout $TIME_OUT sshpass -p ${passwd} ssh -o StrictHostKeyChecking=no -p ${port} ${user}@${host} ${ssh_cmd} 2> /dev/null
    flag=$?
    if [[ $flag -eq 124 ]]; then
        echo "ERROR! ssh -p ${port} ${user}@${host} Error!"
        echo "#################################### End ##############################################"
        exit 1
    elif [[ $flag -ne 0 ]]; then
        return 1
    else
        return 0
    fi
}

function check_roce_network_connection_between_2nodes
{
    # Set ip/host_name or port. 脚本执行节点需要和检测节点互信
    server="${node1} ${port1} ${user1} ${pwd1}"
    client="${node2} ${port2} ${user2} ${pwd2}"
    server_host_ip=${node1}
    client_host_ip=${node2}

    # clean
    ssh_exec $server "pkill -9 ib_send_lat" 2>/dev/null
    ssh_exec $client "pkill -9 ib_send_lat" 2>/dev/null

    # Get ibdev form server and client
    server_ibdev=$(ssh_exec $server "$ib_info_cmd")
    client_ibdev=$(ssh_exec $client "$ib_info_cmd")

    if [ ! -z "$NETWORK_DEVICES" ]; then
        # 用户输入网卡设备名称时，执行该分支
        server_eth_all=($NETWORK_DEVICES)
        client_eth_all=($NETWORK_DEVICES)
        network_devices_num=${#server_eth_all[@]}
        server_mlx_all=()
        client_mlx_all=()
        server_ibdev_active_num=""
        client_ibdev_active_num=""
        server_device_error=()
        client_device_error=()

        for ((m=0; m<$network_devices_num; m++));
        do
            server_network_error_msg=""
            server_mlx_device=$(echo "$server_ibdev" | grep -w ${server_eth_all[$m]} | grep Up | awk '{print $1}')
            if [ -z "$server_mlx_device" ]; then
                server_network_error_msg="${server_network_error_msg} not mlx device or Down"
            fi
            if [ -z "$server_network_error_msg" ]; then
                server_mlx_all+=($server_mlx_device)
            else
                server_device_error+=("${server_eth_all[$m]} ${server_network_error_msg}")
            fi

            client_network_error_msg=""
            client_mlx_device=$(echo "$client_ibdev" | grep -w ${client_eth_all[$m]} | grep Up | awk '{print $1}')
            if [ -z "$client_mlx_device" ]; then
                client_network_error_msg="${client_network_error_msg} not mlx device or Down"
            fi
            if [ -z "$client_network_error_msg" ]; then
                client_mlx_all+=($client_mlx_device)
            else
                client_device_error+=("${client_eth_all[$m]} ${client_network_error_msg}")
            fi
        done

        client_device_error_num=${#client_device_error[@]}
        server_device_error_num=${#server_device_error[@]}
        if [ ${client_device_error_num} -ne 0 ] || [ ${server_device_error_num} -ne 0 ]; then
            # "Network device config Error!"
            for ((s=0; s<${server_device_error_num}; s++));
            do
                echo "ERROR! Server Host ip: ${node1} Error: ${server_device_error[s]}"
            done
            for ((c=0; c<${client_device_error_num}; c++));
            do
                echo "ERROR! Client Host ip: ${node2} Error: ${client_device_error[c]}"
            done
            echo "#################################### End ##############################################"
            exit 1
        fi

        if [[ "${#server_mlx_all[@]}" == "$network_devices_num" ]] && [[ "${#client_mlx_all[@]}" == "$network_devices_num" ]]; then
            server_ibdev_active_num=$network_devices_num
            client_ibdev_active_num=$network_devices_num
        fi

    else
        # 用户未输入网卡设备名称时，通过通用规则获取，执行该分支
        # 前置条件,根据ibdev2netdev，非bond认为是参数面；bond0认为管理面；另外一个bond为存储面。
        # Simple check of dev count
        server_ibdev_active=$(echo "$server_ibdev" | grep -v bond | grep Up)
        client_ibdev_active=$(echo "$client_ibdev" | grep -v bond | grep Up)

        server_ibdev_active_num=$(echo "$server_ibdev_active" | wc -l)
        client_ibdev_active_num=$(echo "$client_ibdev_active" | wc -l)
        if [[ "$server_ibdev_active_num" != "$client_ibdev_active_num" ]]; then
            echo "ERROR! Maybe ibdev down ${node1}: ${server_ibdev}. ${node2}: ${client_ibdev}"
            echo "#################################### End ##############################################"
            exit 1
        fi

        # Get active mlx and eth
        server_mlx_all=$(echo "$server_ibdev_active" | awk '{print $1}')
        client_mlx_all=$(echo "$client_ibdev_active" | awk '{print $1}')
        server_eth_all=$(echo "$server_ibdev_active" | awk '{print $5}')
        client_eth_all=$(echo "$client_ibdev_active" | awk '{print $5}')

        # Change to array
        server_mlx_all=($server_mlx_all)
        client_mlx_all=($client_mlx_all)
        server_eth_all=($server_eth_all)
        client_eth_all=($client_eth_all)
    fi
    # Loop check
    for ((i=0; i<$server_ibdev_active_num; i++));
    do
        for ((j=0; j<$client_ibdev_active_num; j++));
        do
            echo "Start checking ${server_eth_all[$i]} and ${client_eth_all[$j]}"

            server_cmd="ib_send_lat -d ${server_mlx_all[$i]} -x ${GID} -n 5"
            client_cmd="ib_send_lat -d ${client_mlx_all[$j]} -x ${GID} -n 5 ${server_host_ip}"

            # 启动server端（使用后台执行并重定向输出）
            ssh_exec $server "$server_cmd > /dev/null 2>&1 &"
            sleep $ssh_interval

            # 启动client端测试连接
            result=$(ssh_exec $client "$client_cmd" 2>&1)
            client_exit_code=$?

            # 清理进程
            ssh_exec $server "pkill -9 ib_send_lat" 2>/dev/null
            ssh_exec $client "pkill -9 ib_send_lat" 2>/dev/null

            if [[ "$result" == *"#bytes"* ]] && [[ "$result" == *"iterations"* ]]; then
                echo "SUCCESS! RoCE network connection between Server-${node1}-${server_eth_all[$i]} and Client-${node2}-${client_eth_all[$j]} Link Yes!"
                echo "Latency test completed successfully"
            else
                echo "FAILED! RoCE network connection between Server-${node1}-${server_eth_all[$i]} and Client-${node2}-${client_eth_all[$j]} Link No!"
                echo "Client exit code: $client_exit_code"
                if [[ ! -z "$result" ]]; then
                    echo "Error output (last few lines):"
                    echo "$result" | tail -5
                fi
            fi

            sleep 0.1
        done
    done
}

start_time=$(date +%s.%N)
echo "###########Start check RoCE network connection between ${node1} and ${node2}###########"
check_roce_network_connection_between_2nodes
end_time=$(date +%s.%N)
elapsed_time=`echo $end_time $start_time |awk '{printf($1-$2)}'`
echo "Script execution time: $elapsed_time seconds"
echo "#################################### End ##############################################"
