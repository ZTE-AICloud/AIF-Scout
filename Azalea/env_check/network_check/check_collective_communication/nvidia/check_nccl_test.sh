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

tcp_nic=$1
bw_standard=$2
gid_index=$3
gpu_count=$4
algorithm=${5-"all_reduce"}
begin_size=$6
end_size=$7
step_factor=$8
iterations=$9
warmup_iterations=${10}
env_param=${11}
additional_param=${12}
ip_list=${13}
ssh_port=${14}

declare -A algorithm_map=(
    ["all_reduce"]="all_reduce_perf"
    ["all_gather"]="all_gather_perf"
    ["all_to_all"]="alltoall_perf"
    ["reduce_scatter"]="reduce_scatter_perf"
    ["reduce"]="reduce_perf"
    ["broadcast"]="broadcast_perf"
    ["sendrecv"]="sendrecv_perf"
)

ip_list=${ip_list//,/ }
ip_len=`echo $ip_list |wc -w`
nccl_path="/workspace/nccl-tests/build"
perf_file=${algorithm_map[$algorithm]}
[[ -z "$perf_file" ]] && { echo "unkonwn algorithm"; exit 1; }

data_arg="-g $gpu_count -b $begin_size -e $end_size -f $step_factor -n $iterations -w $warmup_iterations"
if [[ -n $additional_param && $additional_param != "None" ]]; then
    data_arg="$data_arg $additional_param"
fi
param_arg="--allow-run-as-root --bind-to none -map-by slot -x LD_LIBRARY_PATH=/usr/local/cuda-12.2/targets/x86_64-linux/lib/"
mpiexec_bin="mpirun"

function export_env_param() {
    env_param=$(echo "$env_param" |sed 's/,/ /g')
    for param in $env_param; do
        if [[ "$param" == *=* ]]; then
            local key="${param%%=*}"
            local value="${param#*=}"
        else
            local key="$param"
            local value=""
        fi
        export "$key"="$value"
    done
    env
}

function check_nccl_test() {
    host_info=""
    for ip in $ip_list; do
        if [[ -z "$host_info" ]]; then
            host_info="$ip"
        else
            host_info="$host_info,$ip"
        fi
    done
    echo "$mpiexec_bin -q --host $host_info $param_arg -x NCCL_IB_GID_INDEX=$gid_index --mca btl_tcp_if_include $tcp_nic --mca plm_rsh_agent \"ssh -p $ssh_port\" -x NCCL_SOCKET_IFNAME=$tcp_nic $nccl_path/$perf_file $data_arg"
    result_info=`$mpiexec_bin -q --host $host_info $param_arg -x NCCL_IB_GID_INDEX=$gid_index --mca btl_tcp_if_include $tcp_nic --mca plm_rsh_agent "ssh -p $ssh_port" -x NCCL_SOCKET_IFNAME=$tcp_nic $nccl_path/$perf_file $data_arg`
}

function check_result() {
    [[ -z "$result_info" ]] && { echo "no nccl test result"; isOk=1; return; }
    echo "$result_info"
    out_algbw=`echo "$result_info" |grep -E "^(\*[[:space:]]*|[[:space:]]*)[0-9]+" |tail -n 1 |awk '{print $(NF-6)}'`
    inplace_algbw=`echo "$result_info" |grep -E "^(\*[[:space:]]*|[[:space:]]*)[0-9]+" |tail -n 1 |awk '{print $(NF-2)}'`
    [[ -z "$out_algbw" ]] && { echo "no outplace algbw result"; isOk=1; }
    [[ -z "$inplace_algbw" ]] && { echo "no inplace algbw result"; isOk=1; }
    echo "[Azalea]out max algbw(GB/s): $out_algbw"
    echo "[Azalea]in max algbw(GB/s): $inplace_algbw"
}

export_env_param
check_nccl_test
check_result
exit $isOk
