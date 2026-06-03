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

SCRIPT_PATH=$(dirname "$0")
help=0
# Get args.
while getopts ":m:" opt; do
    case $opt in
        m) input_manufacturer=$OPTARG ;;
        \?) echo "Invalid option -$OPTARG" >&2; help=1 ;;
    esac
done

if [ $help -eq 1 ]; then
  echo "m) gpu manufacturer"
  echo "H) help"
  exit 1
fi

function load_docker_image() {
    docker image inspect $image_id &> /dev/null
    if [[ $? -ne 0 ]]; then
        sudo docker load -i $image_file
        [[ $? -ne 0 ]] && { echo "load image failed"; exit 1; }
    fi
    docker inspect $docker_name &> /dev/null
    if [[ $? -eq 0 ]]; then
        sudo docker rm -f $docker_name
    fi
}

function check_nvidia_gpu_d2h() {
    image_file="azalea_nvidia_runtime_0.5.tar"
    image_id="azalea_nvidia_runtime:0.5"
    docker_name="azalea_env_check"
    docker_param="-itd --privileged --network host --name $docker_name"
    docker_cmd_param="tail -f /dev/null"
    load_docker_image
    sudo docker run $docker_param --shm-size=64g --gpus all $image_id $docker_cmd_param
    [[ $? -ne 0 ]] && { echo "run test docker failed"; exit 1; }
    sudo docker exec $docker_name bash -lc "python /workspace/tools/d2h.py"
}

cd $SCRIPT_PATH
if [[ "$input_manufacturer" == "NVIDIA" ]]; then
    check_nvidia_gpu_d2h
else
    echo "Unknown gpu manufacturer:$input_manufacturer"
    exit 1
fi
