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

grub_info=`sudo cat /etc/default/grub 2> /dev/null`
echo "$grub_info"
echo "[InspectorRet Table]item,value,result"
cpu_idle=`echo "$grub_info" |grep GRUB_CMDLINE_LINUX |grep -o 'idle=[^ "]*' |awk -F "=" '{print $NF}'`
if [[ $cpu_idle == "poll" ]]; then
    echo "[InspectorRet Table]idle,$cpu_idle,normal"
else
    [[ -z $cpu_idle ]] && { cpu_idle="--"; }
    echo "[InspectorRet Table]idle,$cpu_idle(expected poll),abnormal"
fi
