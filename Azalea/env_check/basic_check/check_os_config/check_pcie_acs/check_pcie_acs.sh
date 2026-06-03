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

check_item="SrcValid TransBlk ReqRedir CmpltRedir UpstreamFwd EgressCtrl DirectTrans"

acs_ctl_info=`lspci -vvv 2> /dev/null |grep ACSCtl`
echo "$acs_ctl_info"
echo "[InspectorRet Table]item,state,result"
for item in $check_item;do
    echo "$acs_ctl_info" |grep -qi "$item+"
    if [[ $? -eq 0 ]]; then
        echo "[InspectorRet Table]$item,not all disabled,abnormal"
    else
        echo "[InspectorRet Table]$item,all disabled,normal"
    fi
done
