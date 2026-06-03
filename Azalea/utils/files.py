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
import json
import logging
import zipfile
from utils.consts import PathConfig


logger = logging.getLogger(__name__)


def get_env_check_item_config():
    file_path = PathConfig.ENV_CHECK_CONFIG_JSON
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        logger.error(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError:
        logger.error(f"Error: The file {file_path} is not a valid JSON file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def zip_files(zip_path, result_path):
    logger.info(f"Result zip path: {result_path}")
    with zipfile.ZipFile(result_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(zip_path):
            for file in files:
                rel_path = os.path.relpath(root, zip_path)
                arcname = os.path.join(rel_path, file)
                zipf.write(os.path.join(root, file), arcname)
    return result_path


def file_iterator_response(file_path, chunk_size=8192):
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
    os.remove(file_path)
