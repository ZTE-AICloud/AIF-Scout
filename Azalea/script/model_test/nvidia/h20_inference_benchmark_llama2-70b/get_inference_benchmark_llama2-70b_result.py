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

import json
import argparse


def extract_performance_metrics(log_file):
    result_dict = {}
    try:
        with open(log_file, 'r') as file:
            for line in file:
                if '[BENCHMARK]' in line:
                    parts = line.strip().split('[BENCHMARK]')[
                        1].strip().split()
                    i = 0
                    while i < len(parts) - 1:
                        key = parts[i]
                        value = parts[i + 1]

                        if key in ["tokens_per_sec"]:
                            if '.' in value:
                                result_dict[key] = float(value)
                            else:
                                result_dict[key] = int(value)
                        i += 2

        print(json.dumps(result_dict))

    except Exception:
        print(json.dumps({}))


def main():
    parser = argparse.ArgumentParser(
        description='Extract performance metrics from a log file.')
    parser.add_argument('--log_file', required=True,
                        help='Path to the log file')
    args = parser.parse_args()
    extract_performance_metrics(args.log_file)


if __name__ == '__main__':
    main()
