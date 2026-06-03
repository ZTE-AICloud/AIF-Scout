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

workspace=`pwd`
server_log="pv/logs/server.log"

function time_now() {
    date +"%Y-%m-%d %H:%M:%S"
}

function create_dirs() {
    mkdir -p db
    mkdir -p pv/logs
    mkdir -p pv/logs/records
    mkdir -p pv/upload/{common_files,model_files,tool_files}
    mkdir -p pv/upload_tmp
    mkdir -p pv/etc
    mkdir -p nginx/{logs,tmp,run}
    mkdir -p pv/etc/nginx.d
}

function delete_server_log() {
    rm -f "$server_log"
}

function run_web_server() {
    echo "$(time_now) Start nginx..." >> "$server_log"
    nginx -p /app/nginx -c conf/nginx.conf >> "$server_log" 2>&1 &

    echo "$(time_now) Start redis-server..." >> "$server_log"
    redis-server --daemonize yes >> "$server_log" 2>&1 &
}

function azalea_conf() {
    [[ ! -f pv/etc/azalea.conf ]] && { cp etc/azalea.conf.default pv/etc/azalea.conf; }
    [[ ! -f etc/azalea.conf ]] && { ln -s ${workspace}/pv/etc/azalea.conf etc/azalea.conf; }
}

function migrate() {
    echo "$(time_now) Begin to migrate..." >> "$server_log"
    python manage.py migrate >> "$server_log" 2>&1
    echo "$(time_now) End to migrate" >> "$server_log"
}

function run_azalea_server() {
    echo "$(time_now) Start daphne..." >> "$server_log"
    daphne -p 9003 azalea.asgi:application >> "$server_log" 2>&1 &

    echo "$(time_now) Start azalea runserver..." >> "$server_log"
    python manage.py runserver --noreload 127.0.0.1:9002 >> "$server_log" 2>&1 &
}

create_dirs
delete_server_log
echo "$(time_now) Begin to start azalea..." > "$server_log"
run_web_server
azalea_conf
migrate
run_azalea_server
echo "$(time_now) azalea server started" >> "$server_log"
tail -f /dev/null
