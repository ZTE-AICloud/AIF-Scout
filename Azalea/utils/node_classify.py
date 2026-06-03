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

import copy
import itertools


def extract_rdma_data(raw_data):
    """
    ['###################Start check RDMA between 10.166.200.201 and 10.166.200.204######################',
    'Start checking mlx5_0 and mlx5_10',
    'True!',
    '',
    'Start checking mlx5_0 and mlx5_11',
    'True!',
    '', '
    Start checking mlx5_0 and mlx5_2',
    'True!',
    '',
    '#################################### End ##############################################',
    'Script execution time: 19.731804204 seconds']
    """
    raw_data = [line for line in raw_data if "Connection" not in line]
    return "\n".join(raw_data)


def classify_nodes(nodes):
    """
    classify nodes
    :param nodes: Command to run
    :type nodes: list
    :return: List[List[Tuple[str]]]
    such as:
    input: ["node1", "node2", "node3", "node4"]
    output:
        [[('node1', 'node2'), ('node2', 'node3'), ('node3', 'node4')],
        [('node1', 'node3'), ('node2', 'node4')],
        [('node1', 'node4')]]
    """
    nodes_num = len(nodes)
    # 生成所有的两两组合
    combine_nodes = []

    for combination in itertools.combinations(nodes, 2):
        combine_nodes.append(combination)
    classified_nodes = repeat_combine(combine_nodes, nodes_num)
    return classified_nodes


def classify_nodes_no_repeat(nodes):
    """
    classify nodes no repeat in the group.
    :param nodes: Command to run
    :type nodes: list
    :return: List[List[Tuple[str]]]
    such as:
    input: ["node1", "node2", "node3", "node4", "node5", "node6", "node7"]
    output:
        [[('node1', 'node2'), ('node3', 'node4'), ('node5', 'node6')],
         [('node1', 'node3'), ('node2', 'node4'), ('node5', 'node7')],
         [('node1', 'node4'), ('node2', 'node3'), ('node6', 'node7')],
         [('node1', 'node5'), ('node2', 'node6'), ('node3', 'node7')],
         [('node1', 'node6'), ('node2', 'node5'), ('node4', 'node7')],
         [('node1', 'node7'), ('node3', 'node5'), ('node4', 'node6')],
         [('node2', 'node7'), ('node3', 'node6')],
         [('node4', 'node5')],
         ]
    """
    # 生成所有的两两组合
    combine_nodes = []

    for combination in itertools.combinations(nodes, 2):
        combine_nodes.append(combination)

    # DEBUG 对照方法
    # nodes_num = len(nodes)
    # classified_nodes = repeat_combine(combine_nodes, nodes_num)
    no_repeat_classified_nodes = no_repeat_combine(combine_nodes)

    return no_repeat_classified_nodes


def classify_nodes_no_repeat_only_one_group(nodes):
    """
    classify nodes no repeat in the group.
    :param nodes: Command to run
    :type nodes: list
    :return: List[List[Tuple[str]]]
    such as:
    input: ["node1", "node2", "node3", "node4", "node5", "node6", "node7"]
    output:
        [[('node1', 'node2'), ('node3', 'node4'), ('node5', 'node6')],
         ]
    """
    # 生成所有的两两组合
    combine_nodes = []

    if len(nodes) < 2:
        return []
    for combination in itertools.combinations(nodes, 2):
        combine_nodes.append(combination)

    no_repeat_groups = []
    sub_group = [combine_nodes.pop(0)]
    for pair in combine_nodes:
        if all(pair[0] not in exist_pair and pair[1] not in exist_pair
               for exist_pair in sub_group):
            sub_group.append(pair)
            combine_nodes.remove(pair)
    # print(sub_group)
    no_repeat_groups.append(sub_group)
    # DEBUG
    # counts(no_repeat_groups, 3)
    return no_repeat_groups


def repeat_combine(nodes_pairs, no_repeat_nodes_num):
    """
    classify nodes repeat in the group core.
    :param nodes_pairs: List[Tuple[str]]
    :param no_repeat_nodes_num int
    :return: List[List[Tuple[str]]]
    such as:
    input: ([('node1', 'node2'), ('node1', 'node3'), ('node1', 'node4'),
             ('node2', 'node3'), ('node2', 'node4'),
             ('node3', 'node4')],
            4)
    output:
        [[('node1', 'node2'), ('node2', 'node3'), ('node3', 'node4')],
        [('node1', 'node3'), ('node2', 'node4')],
        [('node1', 'node4')]]
    """
    combine_num = len(nodes_pairs)
    classified_nodes = []
    for i in range(no_repeat_nodes_num - 1):
        sub_combine = []
        for j in range(no_repeat_nodes_num):
            index = int(j * no_repeat_nodes_num - j * (j + 1) / 2 + i)
            if index > (combine_num - 1 - i * (i + 1) / 2):
                break
            sub_combine.append(nodes_pairs[index])
        classified_nodes.append(sub_combine)

    # DEBUG
    # counts(classified_nodes, 1)
    return classified_nodes


def no_repeat_combine(nodes_pairs):
    """
    classify nodes no repeat in the group core.
    :param nodes_pairs: List[Tuple[str]]
    :return: List[List[Tuple[str]]]
    input: ["node1", "node2", "node3", "node4", "node5", "node6", "node7"]
    output:
        [[('node1', 'node2'), ('node3', 'node4'), ('node5', 'node6')],
         [('node1', 'node3'), ('node2', 'node4'), ('node5', 'node7')],
         [('node1', 'node4'), ('node2', 'node3'), ('node6', 'node7')],
         [('node1', 'node5'), ('node2', 'node6'), ('node3', 'node7')],
         [('node1', 'node6'), ('node2', 'node5'), ('node4', 'node7')],
         [('node1', 'node7'), ('node3', 'node5'), ('node4', 'node6')],
         [('node2', 'node7'), ('node3', 'node6')],
         [('node4', 'node5')],
         ]
    """
    # print("inputs: ", nodes_pairs)
    nodes_pairs_duplication = copy.deepcopy(nodes_pairs)
    no_repeat_groups = []
    no_repeat_combine_core(no_repeat_groups, nodes_pairs_duplication)
    # print(no_repeat_groups, nodes_pairs_duplication)

    # DEBUG
    # counts(no_repeat_groups, 2)
    return no_repeat_groups


def no_repeat_combine_core(no_repeat_groups, groups):
    # 递归分类，保证同一组内，一台机器只能出现一次
    # return None, due to param inplace change
    if not groups:
        return
    # print(groups)
    sub_group = [groups.pop(0)]
    for pair in groups:
        if all(pair[0] not in exist_pair and pair[1] not in exist_pair
               for exist_pair in sub_group):
            sub_group.append(pair)
            groups.remove(pair)
    # print(sub_group)
    no_repeat_groups.append(sub_group)
    return no_repeat_combine_core(no_repeat_groups, groups)


def counts(all_groups, id=None):
    # 使用列表推导式计算每个子列表的长度，然后用sum函数求和
    sum_of_elements = sum(len(group) for group in all_groups)
    print(f"method{id}: group num {len(all_groups)} pairs: {sum_of_elements}")
