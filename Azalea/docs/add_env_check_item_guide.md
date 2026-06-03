# Azalea 环境检测增加检查项指南

本文档详细说明如何在 Azalea 项目中添加新的环境检测项。

---

## 📋 目录

- [概述](#概述)
- [检测项组成](#检测项组成)
- [添加步骤](#添加步骤)
- [配置文件详解](#配置文件详解)
- [代码实现详解](#代码实现详解)
- [常见问题](#常见问题)

---

## 🎯 概述

在 Azalea 中添加新的环境检测项需要完成三个主要步骤：

1. **配置检测项信息** - 在 JSON 配置文件中定义检测项的元数据和参数
2. **添加到菜单** - 将检测项添加到相应的菜单分类中
3. **实现检测逻辑** - 编写 Python 类和 Shell 脚本实现具体检测逻辑

---

## 🧩 检测项组成

一个完整的检测项包含以下部分：

```
检测项
├── 配置信息 (JSON)
│   ├── 检测项定义 (environment_check_item.json)
│   └── 菜单配置 (basic_check_menu.json 或 network_check_menu.json)
├── Python 实现
│   ├── 检测任务类 (继承自 Task)
│   └── __init__.py (导出类)
└── Shell 脚本 (可选)
    └── 具体检测脚本 (.sh)
```

---

## 🚀 添加步骤

### 步骤 1: 配置检测项信息

编辑 `etc/environment_check/environment_check_item.json`，添加检测项定义：

```json
{
  "your_check_item_key": {
    "key": "your_check_item_key",
    "name_en": "Your Check Item Name",
    "name_zh": "你的检测项名称",
    "isSelected": true,
    "description_en": "Description of your check item",
    "description_zh": "检测项描述",
    "param": [
      {
        "key": "param_key",
        "name_en": "Parameter Name",
        "name_zh": "参数名称",
        "default_value": "default_value",
        "value_type": "string",
        "required": true,
        "notice_en": "Parameter notice",
        "notice_zh": "参数说明"
      }
    ]
  }
}
```

### 步骤 2: 添加到菜单

**基础检查** - 编辑 `etc/environment_check/basic_check_menu.json`：

```json
[
  {
    "key": "your_category",
    "name_en": "Your Category",
    "name_zh": "你的分类",
    "check_item": [
      "your_check_item_key"
    ]
  }
]
```

**网络检查** - 编辑 `etc/environment_check/network_check_menu.json`：

```json
[
  {
    "key": "your_network_category",
    "name_en": "Your Network Category",
    "name_zh": "你的网络分类",
    "check_item": [
      "your_check_item_key"
    ]
  }
]
```

### 步骤 3: 实现检测逻辑

#### 3.1 创建目录结构

```bash
# 基础检查
mkdir -p env_check/basic_check/your_category/your_check_item

# 网络检查
mkdir -p env_check/network_check/your_category/your_check_item
```

#### 3.2 创建 Python 检测类

创建 `env_check/basic_check/your_category/your_check_item/your_check_item.py`：

```python
# Copyright 2025 ZTE Corporation.
# All Rights Reserved.

import logging
import os
from typing import List
from pssh.config import HostConfig
from pssh.output import HostOutput

from env_check.base import Task, TaskMetadata
from utils.ssh_tool import copy_file_to_multi_hosts, exec_cmd_on_multi_hosts_realtime
from utils.consts import TaskStatus, TaskResult

logger = logging.getLogger(__name__)

# Shell 脚本文件名
SHELL_SCRIPT = "your_check_script.sh"
CURRENT_DIR = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(CURRENT_DIR, SHELL_SCRIPT)
DEST_PATH = os.path.join(Task.REMOTE_WORKSPACE, SHELL_SCRIPT)


class YourCheckTask(Task):
    """你的检测任务类"""

    # SSH 执行超时时间（秒）
    PSSH_EXEC_TIMEOUT = 120

    # 是否同步更新节点检查状态
    sync_check_node = True

    # 任务元数据
    metadata = TaskMetadata(
        check_item="your_check_item_key",
    )

    def execute(self) -> None:
        """执行检测任务"""
        try:
            # 更新检测项状态为进行中
            self.save_check_item_progress(
                TaskStatus.INPROGRESS.value,
                "Start exec your check..."
            )
            logger.info("Start exec your check...")

            # 验证是否选择了节点
            if len(self.task_options.nodes) == 0:
                self.save_check_item_progress(
                    TaskStatus.FAILED.value, "no node selected"
                )
                logger.error("no node selected")
                return

            # 准备节点信息
            host_ips = []
            host_config = []
            node_ids = {}
            for node in self.task_options.nodes:
                host_ips.append(node.ip_address)
                host_config.append(
                    HostConfig(
                        user=node.username,
                        port=node.port,
                        password=node.ssh_password
                    )
                )
                node_ids[node.ip_address] = node.node_id

            # 获取检测参数
            param1 = self.task_options.task_params.get("param_key")

            # 分发执行脚本到目标节点
            copy_file_to_multi_hosts(
                host_ips,
                host_config,
                LOCAL_PATH,
                DEST_PATH,
                raise_error=False
            )

            # 在多个节点上执行命令
            host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
                host_ips,
                host_config,
                f"chmod +x {DEST_PATH} && {DEST_PATH} '{param1}'",
                timeout=self.PSSH_EXEC_TIMEOUT,
                stop_on_errors=False,
            )

            logger.debug(host_output)
            # 处理执行结果
            self._handle_result(host_output, node_ids)

        except Exception as e:
            self.save_check_item_progress(
                TaskStatus.FAILED.value, f"Exception: {e}"
            )
            logger.error(f"Your check exception: {e}")

    def _handle_result(self, host_output, node_ids):
        """处理检测结果"""
        abnormal_host = []

        for o in host_output:
            detail_result = []
            format_result = {
                "result_type": "table",
                "data": [["Item", "Actual", "Expected", "Result"]],
            }

            node_id = node_ids.get(o.host)

            # 处理异常情况
            if o.exception:
                abnormal_host.append(o.host)
                formatted_message = self.format_exception(o.exception)
                self.save_check_result_progress(
                    [node_id],
                    TaskStatus.FAILED.value,
                    f"{o.host} raise an exception: {formatted_message}",
                    sync_check_node=self.sync_check_node,
                )
                continue

            # 处理正常输出
            stdout = list(o.stdout)
            stderr = list(o.stderr)

            # 解析输出结果
            for line in stdout:
                detail_result.append(line)
                # 根据实际情况解析输出

            # 判断检测是否通过
            is_check_ok = (o.exit_code == 0)
            status = (
                TaskStatus.SUCCESS.value
                if is_check_ok
                else TaskStatus.FAILED.value
            )

            if status == TaskStatus.FAILED.value:
                abnormal_host.append(o.host)

            # 保存结果
            detail_result.append(o.host + " exec " + status)
            detail_result.extend(stderr)

            self.save_check_result_progress(
                [node_id],
                status,
                o.host + " exec " + status,
                detail_result,
                [format_result],
                self.sync_check_node,
            )

        # 更新检测项整体状态
        msg = ""
        if len(abnormal_host) > 0:
            status = TaskStatus.FAILED.value
            msg = "check abnormal host: {}".format(abnormal_host)
            logger.warning(msg)
        else:
            status = TaskStatus.SUCCESS.value

        self.save_check_item_progress(status, msg)
```

#### 3.3 创建 __init__.py

创建 `env_check/basic_check/your_category/__init__.py`：

```python
from .your_check_item import YourCheckTask
```

#### 3.4 创建 Shell 脚本（可选）

创建 `env_check/basic_check/your_category/your_check_item/your_check_script.sh`：

```bash
#!/bin/bash
#
# Copyright 2025 ZTE Corporation.
# All Rights Reserved.

# 接收参数
PARAM1=$1

# 执行检测逻辑
function your_check_function() {
    # 你的检测逻辑
    result=$(some_command)

    # 输出结果（使用 [InspectorRet] 前缀）
    echo "[InspectorRet]Check result: $result"
}

# 调用检测函数
your_check_function
```

赋予执行权限：

```bash
chmod +x env_check/basic_check/your_category/your_check_item/your_check_script.sh
```

### 步骤 4: 注册检测任务

编辑 `env_check/config.py`，添加导入和注册：

```python
# 在导入部分添加
from env_check.basic_check.your_category import YourCheckTask

# 在 CheckTasks 列表中添加
CheckTasks: List[Task] = [
    # ... 其他检测任务 ...
    YourCheckTask,
]
```

### 步骤 5: 测试检测项

1. 重启 Azalea 服务
2. 登录 Web 界面
3. 创建新的环境检测任务
4. 选择你的新检测项
5. 配置参数并执行
6. 查看检测结果

---

## 📝 配置文件详解

### environment_check_item.json 配置结构

```json
{
  "check_item_key": {
    // 必填字段
    "key": "check_item_key",              // 检测项唯一标识
    "name_en": "English Name",            // 英文名称
    "name_zh": "中文名称",                 // 中文名称
    "isSelected": true,                   // 是否默认选中
    "description_en": "English desc",     // 英文描述
    "description_zh": "中文描述",          // 中文描述

    // 可选：检测参数配置
    "param": [
      {
        "key": "param_name",              // 参数键名
        "name_en": "Parameter Name",      // 英文名称
        "name_zh": "参数名称",             // 中文名称
        "default_value": 100,             // 默认值
        "value_type": "number",           // 值类型
        "required": true,                 // 是否必填
        "min": 1,                         // 最小值（数字类型）
        "max": 1000,                      // 最大值（数字类型）
        "precision": 2,                   // 精度（数字类型）
        "unit_en": "MB/s",               // 单位英文
        "unit_zh": "MB/s",               // 单位中文
        "notice_en": "Notice text",       // 提示信息英文
        "notice_zh": "提示信息",           // 提示信息中文

        // 隐藏条件（可选）
        "hidden": [
          {
            "compare_key": "other_param.key",
            "compare_values": ["", null],
            "compare_include": true
          }
        ]
      }
    ]
  }
}
```

### 参数值类型说明

#### 1. string - 字符串类型

```json
{
  "key": "device_name",
  "name_zh": "设备名称",
  "default_value": "eth0",
  "value_type": "string",
  "required": true,
  "notice_zh": "多个设备使用','分割"
}
```

#### 2. number - 数字类型

```json
{
  "key": "threshold",
  "name_zh": "阈值",
  "default_value": 100,
  "value_type": "number",
  "min": 1,
  "max": 1000,
  "precision": 2,
  "unit_zh": "MB/s",
  "required": true
}
```

#### 3. selector - 选择器类型

```json
{
  "key": "mode",
  "name_zh": "模式",
  "default_value": "mode1",
  "value_type": "selector",
  "selector_option": ["mode1", "mode2", "mode3"],
  "required": true
}
```

或者使用对象形式：

```json
{
  "key": "enable",
  "name_zh": "是否启用",
  "value_type": "selector",
  "selector_option": [
    {
      "label_en": "true",
      "label_zh": "是",
      "value": "true"
    },
    {
      "label_en": "false",
      "label_zh": "否",
      "value": "false"
    }
  ],
  "required": true
}
```

### 菜单配置结构

```json
[
  {
    "key": "category_key",              // 分类唯一标识
    "name_en": "Category Name",         // 英文名称
    "name_zh": "分类名称",               // 中文名称
    "check_item": [                     // 包含的检测项
      "check_item_key_1",
      "check_item_key_2"
    ]
  }
]
```

---

## 💻 代码实现详解

### Task 基类说明

所有检测任务都继承自 `env_check.base.Task` 基类：

```python
class Task(ABC):
    """检测任务基类"""

    # SSH 执行超时时间
    PSSH_EXEC_TIMEOUT = 60

    # 远程工作目录
    REMOTE_WORKSPACE = PathConfig.REMOTE_WORKSPACE

    # 工具文件目录
    TOOL_FILE_DIR = PathConfig.UPLOAD_TOOL_FILE_PATH

    def __init__(self):
        self.task_options: Optional[TaskOptions] = None
        self.env_check_item: Optional[models.EnvCheckItem] = None
        self.results: Dict[str, models.EnvCheckResult] = {}

    @property
    @abstractmethod
    def metadata(self) -> TaskMetadata:
        """任务元数据（必须实现）"""
        pass

    @abstractmethod
    def execute(self) -> None:
        """执行检测任务（必须实现）"""
        pass

    def stop(self):
        """停止检测任务（可选实现）"""
        pass
```

### 重要方法说明

#### 1. save_check_item_progress()

更新检测项的执行状态：

```python
self.save_check_item_progress(
    status,  # TaskStatus.INPROGRESS / SUCCESS / FAILED
    msg=""   # 状态消息
)
```

#### 2. save_check_result_progress()

保存单个节点的检测结果：

```python
self.save_check_result_progress(
    nodes=[node_id],              # 节点ID列表
    status=TaskStatus.SUCCESS,    # 结果状态
    msg="exec success",           # 结果消息
    detail_result=[...],          # 详细结果（字符串列表）
    format_result=[...],          # 格式化结果（表格/图表）
    sync_check_node=True          # 是否同步更新节点状态
)
```

#### 3. format_result 结构

格式化结果用于前端展示，支持表格格式：

```python
format_result = {
    "result_type": "table",
    "data": [
        ["列标题1", "列标题2", "列标题3", "列标题4"],
        ["数据1", "数据2", "数据3", "normal"],
        ["数据1", "数据2", "数据3", "abnormal"],
    ]
}
```

### SSH 工具方法

#### 1. copy_file_to_multi_hosts()

将文件复制到多个节点：

```python
from utils.ssh_tool import copy_file_to_multi_hosts

copy_file_to_multi_hosts(
    host_ips,        # IP地址列表
    host_config,     # HostConfig列表
    local_path,      # 本地文件路径
    dest_path,       # 目标路径
    raise_error=False
)
```

#### 2. exec_cmd_on_multi_hosts_realtime()

在多个节点上执行命令：

```python
from utils.ssh_tool import exec_cmd_on_multi_hosts_realtime

host_output: List[HostOutput] = exec_cmd_on_multi_hosts_realtime(
    host_ips,        # IP地址列表
    host_config,     # HostConfig列表
    command,         # 要执行的命令
    timeout=120,     # 超时时间（秒）
    stop_on_errors=False
)
```

#### 3. HostOutput 结构

```python
for output in host_output:
    output.host        # 主机IP
    output.stdout      # 标准输出（生成器）
    output.stderr      # 标准错误（生成器）
    output.exit_code   # 退出码
    output.exception   # 异常信息（如果有）
```

---

## ❓ 常见问题

### Q1: 检测项不显示在 Web 界面？

**检查清单：**
1. 是否在 `environment_check_item.json` 中正确配置
2. 是否添加到菜单配置文件中
3. 是否在 `env_check/config.py` 中注册
4. 是否重启了 Azalea 服务
5. 浏览器是否刷新缓存

### Q2: 执行检测时报错 "Not support check item"？

**原因：** 检测任务类未正确注册

**解决方案：**
1. 检查 `metadata.check_item` 是否与配置文件中的 `key` 一致
2. 确认在 `env_check/config.py` 中已导入并添加到 `CheckTasks`

### Q3: SSH 连接超时？

**原因：** 超时时间设置过短或网络延迟

**解决方案：**
```python
class YourCheckTask(Task):
    PSSH_EXEC_TIMEOUT = 300  # 增加超时时间
```

### Q4: Shell 脚本没有执行权限？

**解决方案：**
```bash
chmod +x env_check/basic_check/your_category/your_check_item/*.sh
```

### Q5: 如何调试检测项？

**查看日志**
```bash
vi /app/pv/logs/azalea.log
```

### Q6: 如何实现参数联动？

使用 `hidden` 配置实现参数条件显示：

```json
{
  "key": "advanced_param",
  "name_zh": "高级参数",
  "hidden": [
    {
      "compare_key": "enable_advanced",
      "compare_values": ["false"],
      "compare_include": true
    }
  ]
}
```

### Q7: 如何支持不同 GPU 厂商？

根据节点的 GPU 厂商信息分别处理：

```python
for node in self.task_options.nodes:
    if node.gpu_manufacturer == GpuManufacturer.NVIDIA.value:
        # NVIDIA GPU 处理逻辑
        pass
    elif node.gpu_manufacturer == "AMD":
        # AMD GPU 处理逻辑
        pass
```
