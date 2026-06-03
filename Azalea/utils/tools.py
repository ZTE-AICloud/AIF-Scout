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

import hashlib
import ipaddress
import re
import logging

logger = logging.getLogger(__name__)


def is_valid_ip(ip_str: str) -> bool:
    try:
        _ = ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def format_exception(e):
    placeholder_pattern = r"(%[sdioxXeEfFgG])"

    if (
        len(e.args) == 1
        and isinstance(e.args[0], str)
        and re.search(placeholder_pattern, e.args[0])
    ):
        try:
            logger.info("1 - Formatting string-style args")
            input_str = e.args[0]
            pattern = r"\(([^,]*)"
            match = re.match(pattern, input_str)
            template = match.group(1)

            parts = input_str[match.end():].strip(",").strip("()").split(", ")
            parts = [part.strip().strip("'\"") for part in parts]
            result = template % tuple(parts)

            return result
        except Exception as ex:
            logger.warning(
                f"Failed to format extracted string with args: {ex}")

    else:
        try:
            logger.info("2 - Formatting tuple-style args")
            formatted_message = e.args[0] % e.args[1:]
            return formatted_message
        except Exception as ex:
            logger.warning(f"Failed to format tuple-style args: {ex}")

    logger.info("3 - Falling back to str(e)")
    return str(e)


def consistent_hash_id(input_string):
    return hashlib.blake2s(input_string.encode("utf-8")).hexdigest()


def list_to_unique_str(lst):
    """
    # 示例
    list_a = [3, 1, 2]
    list_b = [1, 2, 3]
    print(list_to_unique_str(list_a))  # 输出: "1-2-3"
    print(list_to_unique_str(list_b))  # 输出: "1-2-3"
    """
    # 对列表排序 → 转换为字符串 → 用分隔符连接
    return "-".join(map(str, sorted(lst)))


def get_src_in_dst_list(src_lst, dst_lst):
    if src_lst is None or dst_lst is None or len(src_lst) == 0 or len(dst_lst) == 0:
        return []
    dst_set = set(dst_lst)
    return [src for src in src_lst if src in dst_set]


def is_number(var):
    return isinstance(var, (int, float)) and not isinstance(var, bool)


def natural_sort_key(s):
    """将字符串中的数字部分转为整数，便于排序"""
    return [
        int(token) if token.isdigit() else token
        for token in re.findall(r'\d+|\D+', s)
    ]


def change_model_item_to_str(s):
    return str(s) if s is not None else ""
