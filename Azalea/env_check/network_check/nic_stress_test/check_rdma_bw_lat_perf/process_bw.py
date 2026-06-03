# -*- coding: utf-8 -*-
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

import os
import glob
import re
import csv
import logging

logger = logging.getLogger(__name__)

add_info_patterns = {
    "Client Host": r"Client Host: ([^\s]+)",
    "Client Device": r"Client Device: ([^\s]+)",
    "Server Host": r"Server Host: ([^\s]+)",
    "Server Device": r"Server Device: ([^\s]+)",
    "Number of qps": r"Number of qps\s+:\s+(\d+)",
}

header_pattern = "#bytes"

data_keys = [
    "#bytes",
    "#iterations",
    "BW peak[Gb/sec]",
    "BW average[Gb/sec]",
    "MsgRate[Mpps]",
    "CPU_Util[%]",
]

all_keys = [
    "Client Host",
    "Client Device",
    "Server Host",
    "Server Device",
    "Number of qps",
] + data_keys


def extract_key_value_pairs(content):
    extracted_info = {}
    for k in data_keys:
        extracted_info[k] = []

    for key, pattern in add_info_patterns.items():
        match = re.search(pattern, content)
        if match:
            extracted_info[key] = match.group(1)

    lines = content.splitlines()
    parsing_data = False

    for line in lines:
        if line.lstrip().startswith(header_pattern):
            parsing_data = True
            continue
        if parsing_data and not line.lstrip().startswith("---"):
            i = 0
            for d in line.strip().split():
                if i > len(data_keys) - 1:
                    break
                extracted_info[data_keys[i]].append(d.strip())
                i = i + 1

    return extracted_info


def read_perf_files(directory, recursive=False):
    if recursive:
        perf_files = glob.glob(os.path.join(
            directory, "**", "*.perf"), recursive=True)
    else:
        perf_files = glob.glob(os.path.join(directory, "*.perf"))

    file_info = {}

    for file_path in perf_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                extracted_info = extract_key_value_pairs(content)
                file_info[file_path] = extracted_info
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
    return file_info


def export_csv(directory_path, recursive=False):
    perf_file_info = read_perf_files(directory_path, recursive)
    datas = perf_file_info.values()
    keys = list(all_keys)
    dir_name = os.path.basename(directory_path)

    with open(f"{directory_path}/{dir_name}.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        for item in datas:
            for i in range(len(item["#bytes"])):
                row = {
                    key: item.get(key, [""])[i]
                    if isinstance(item.get(key, []), list) and len(item.get(key, [])) > i
                    else item.get(key, "")
                    for key in keys
                }
                writer.writerow(row)
    logger.info("CSV file has been written successfully.")
