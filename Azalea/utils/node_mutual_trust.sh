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

isOk=0

host_infos=$*

ip_list=$1
user_list=$2
pwd_list=$3
port_list=$4

ip_list=(${ip_list//,/ })
user_list=(${user_list//,/ })
pwd_list=(${pwd_list//,/ })
port_list=(${port_list//,/ })


function gen_ssh_key() {
    if [ ! -f ~/.ssh/id_rsa.pub ];then
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N '' &> /dev/null
    fi
}

function trust_ssh_connect() {
    for host_info in $host_infos; do
        host_info=${host_info//,/ }
        ip=`echo $host_info |awk '{print $1}'`
        user=`echo $host_info |awk '{print $2}'`
        pwd=`echo $host_info |awk '{print $3}'`
        port=`echo $host_info |awk '{print $4}'`
        ifconfig |grep -w "$ip" &> /dev/null
        [[ $? -eq 0 ]] && { continue; }
#        echo "sshpass -p $pwd ssh-copy-id -o StrictHostKeyChecking=no -f -i ~/.ssh/id_rsa.pub -p ${port} $user@${ip}"
        sshpass -p $pwd ssh-copy-id -o StrictHostKeyChecking=no -f -i ~/.ssh/id_rsa.pub -p ${port} $user@${ip} &> /dev/null
        [[ $? -ne 0 ]] && { isOk=1; }
    done
}

gen_ssh_key
trust_ssh_connect
exit $isOk
