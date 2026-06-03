# Azalea 模型测试适配任务添加指南

本文档详细说明如何在 Azalea 项目中添加新的模型测试适配任务（预训练/推理性能/推理精度等）。

---

## 📋 目录

- [概述](#概述)
- [模型测试组成](#模型测试组成)
- [添加步骤](#添加步骤)
- [配置文件详解](#配置文件详解)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 🎯 概述

Azalea 的模型测试框架提供了灵活的插件化架构，支持快速适配新的模型测试任务。

### 支持的测试类型

- 🚀 **预训练** - Pre-training Performance
- 📊 **推理性能** - Inference Performance
- 🎯 **推理精度** - Inference Accuracy
- ⏱️ **推理时延** - Inference Latency
- 🔄 **长稳压测** - Long-term Stability Test
- 🎨 **自定义测试** - Custom Tests

### 核心优势

- ✅ **配置化驱动** - 无需修改核心代码
- ✅ **多厂商支持** - 灵活适配不同GPU厂商
- ✅ **Docker隔离** - 环境隔离，互不干扰
- ✅ **流程可控** - 完整的生命周期管理
- ✅ **结果标准化** - 统一的结果格式

---

## 🧩 模型测试组成

一个完整的模型测试任务包含以下部分：

```
模型测试任务
├── 参数配置 (model_testing_param.json)
│   ├── 测试参数定义
│   └── 期望结果定义
├── 流程配置 (model_testing_configure.yml)
│   ├── 预处理命令
│   ├── 任务执行命令
│   ├── 后处理命令
│   ├── 进度查询命令
│   └── 结果提取命令
└── 测试脚本 (script/model_test/)
    ├── 主执行脚本
    ├── 进度查询脚本
    └── 结果解析脚本
```

---

## 🚀 添加步骤

### 步骤 1: 定义测试参数

编辑 `etc/model_testing/model_testing_param.json`，添加测试任务参数定义：

```json
{
  "your_model_test": {
    "GPU_VENDOR": {
      "GPU_TYPE": {
        "params": [
          {
            "key": "param_name",
            "name_en": "Parameter Name",
            "name_zh": "参数名称",
            "default_value": "default",
            "value_type": "number",
            "required": true,
            "min": 1,
            "precision": 0
          }
        ],
        "expected_result": [
          {
            "key": "metric_name",
            "name_en": "Metric Name",
            "name_zh": "指标名称",
            "default_value": 1000,
            "value_type": "number",
            "min": 0,
            "precision": 2,
            "compare": "min"
          }
        ]
      }
    }
  }
}
```

### 步骤 2: 配置测试流程

编辑 `etc/model_testing/model_testing_configure.yml`，添加测试流程配置：

```yaml
your_model_test:
  GPU_VENDOR:
    GPU_TYPE:
      pre_cmd:
        - "预处理命令1"
        - "预处理命令2"
      task_cmd:
        - "任务执行命令1"
        - "任务执行命令2"
      post_cmd:
        - "后处理命令1"
        - "后处理命令2"
      scp_file:
        - "/app/script/model_test/path/to/script1.sh"
        - "/app/script/model_test/path/to/script2.py"
      params:
        entry_script: main_script.sh
        image_id: docker_image:tag
        param1: value1
        query_interval: 1
      task_timeout: 120
      task_estimated_time: 60
      result: "结果提取命令"
      progress: "进度查询命令"
      download_file:
        - "{remote_data_path}/log_file.log"
```

### 步骤 3: 编写测试脚本

#### 3.1 创建目录结构

```bash
mkdir -p script/model_test/gpu_vendor/gpu_type_your_test
cd script/model_test/gpu_vendor/gpu_type_your_test
```

#### 3.2 创建主执行脚本

创建 `run_your_test.sh`：

```bash
#!/bin/bash
#
# Copyright 2025 ZTE Corporation.
# All Rights Reserved.

# 接收参数
LOG_FILE=${1:-"test.log"}
task_name=${2:-"test"}
param1=${3:-"default"}

# 执行测试
echo "Starting test..." >> $LOG_FILE

# 你的测试逻辑
your_test_command \
    --param1 ${param1} \
    >> $LOG_FILE 2>&1

# 检查结果
if [[ $? -eq 0 ]]; then
    echo "Test task end success" >> $LOG_FILE
    exit 0
else
    echo "Test task end failed" >> $LOG_FILE
    exit 1
fi
```

#### 3.3 创建进度查询脚本

创建 `get_your_test_progress.sh`：

```bash
#!/bin/bash
#
# Copyright 2025 ZTE Corporation.
# All Rights Reserved.

log_file=$1
task_docker="$2"
task_script="$3"

function is_task_still_running() {
    sudo docker ps 2> /dev/null |grep -w "$task_docker" &> /dev/null
    [[ $? -ne 0 ]] && { return 1; }
    sudo docker top "$task_docker" 2> /dev/null |grep "$task_script" &> /dev/null
    [[ $? -ne 0 ]] && { return 1; }
    return 0
}

if [[ ! -f "$log_file" ]]; then
    echo "exception:log file not found"
    exit 0
fi

log_content=$(cat "$log_file" 2> /dev/null)

# 检查失败标记
echo "$log_content" | grep 'Test task end failed' &> /dev/null
[[ $? -eq 0 ]] && { echo "exception:test task end failed"; exit 0; }

# 检查成功标记
echo "$log_content" | grep 'Test task end success' &> /dev/null
[[ $? -eq 0 ]] && { echo 100; exit 0; }

# 检查任务是否还在运行
is_task_still_running
[[ $? -ne 0 ]] && { echo "exception:task terminated abnormally"; exit 0; }

# 计算进度（根据实际情况）
# 示例：基于日志行数估算
progress=50
echo $progress
```

#### 3.4 创建结果解析脚本

创建 `get_your_test_result.py`：

```python
#!/usr/bin/env python3
# Copyright 2025 ZTE Corporation.
# All Rights Reserved.

import json
import argparse
import re


def extract_metrics(log_file):
    """从日志文件中提取性能指标"""
    result_dict = {}

    try:
        with open(log_file, 'r') as file:
            for line in file:
                # 根据实际日志格式解析
                if '[METRIC]' in line:
                    # 示例：[METRIC] metric_name: 1234.56
                    match = re.search(r'\[METRIC\]\s+(\w+):\s+([\d.]+)', line)
                    if match:
                        key = match.group(1)
                        value = match.group(2)

                        if '.' in value:
                            result_dict[key] = float(value)
                        else:
                            result_dict[key] = int(value)

        print(json.dumps(result_dict))

    except Exception as e:
        print(json.dumps({}))


def main():
    parser = argparse.ArgumentParser(
        description='Extract performance metrics from a log file.')
    parser.add_argument('--log_file', required=True,
                        help='Path to the log file')
    args = parser.parse_args()
    extract_metrics(args.log_file)


if __name__ == '__main__':
    main()
```

#### 3.5 设置脚本权限

```bash
chmod +x run_your_test.sh
chmod +x get_your_test_progress.sh
chmod +x get_your_test_result.py
```

### 步骤 4: 测试验证

1. 重启 Azalea 服务
2. 登录 Web 界面
3. 创建新的模型测试任务
4. 选择你的测试类型
5. 配置参数并执行
6. 查看测试结果

---

## 📝 配置文件详解

### model_testing_param.json 详解

#### 整体结构

```json
{
  "测试类型key": {
    "GPU厂商": {
      "GPU型号": {
        "params": [...],
        "expected_result": [...]
      }
    }
  }
}
```

#### 参数配置 (params)

```json
{
  "key": "参数键名",
  "name_en": "英文名称",
  "name_zh": "中文名称",
  "default_value": "默认值",
  "value_type": "值类型",
  "required": true/false,
  "min": 最小值,
  "max": 最大值,
  "precision": 精度,
  "notice_en": "英文提示",
  "notice_zh": "中文提示"
}
```

**支持的值类型**：
- `number` - 数字类型
- `string` - 字符串类型
- `selector` - 选择器类型

#### 期望结果配置 (expected_result)

```json
{
  "key": "指标键名",
  "name_en": "英文名称",
  "name_zh": "中文名称",
  "default_value": 默认期望值,
  "value_type": "number",
  "min": 0,
  "precision": 2,
  "compare": "min" | "max" | "range"
}
```

**对比模式**：
- `min` - 实际值 ≥ 期望值
- `max` - 实际值 ≤ 期望值
- `range` - 期望值范围（需同时设置min和max）

### model_testing_configure.yml 详解

#### 整体结构

```yaml
测试类型key:
  GPU厂商:
    GPU型号:
      pre_cmd: []
      task_cmd: []
      post_cmd: []
      scp_file: []
      params: {}
      task_timeout: 数字
      task_estimated_time: 数字
      result: "命令"
      progress: "命令"
      download_file: []
```

#### 命令配置详解

**1. pre_cmd - 预处理命令**

在任务执行前运行，用于环境准备：

```yaml
pre_cmd:
  - "rm -rf {remote_data_path}; mkdir -p {remote_data_path}"
  - "sudo docker ps -a |grep -w {docker_name} && sudo docker stop {docker_name}; sudo docker rm -f {docker_name} || true"
```

**常见用途**：
- 创建工作目录
- 清理旧容器
- 准备数据文件
- 设置环境变量

**2. task_cmd - 任务执行命令**

核心测试任务的执行命令：

```yaml
task_cmd:
  - "cd {remote_data_path} && git clone https://github.com/repo/model.git"
  - "sudo docker pull {image_id}"
  - "sudo docker run -itd --gpus all --name {docker_name} {image_id}"
  - "sudo docker exec -d {docker_name} bash /workspace/{entry_script} {param1} {param2}"
```

**执行流程**：
1. 准备代码和数据
2. 拉取Docker镜像
3. 启动Docker容器
4. 在容器中执行测试

**3. post_cmd - 后处理命令**

任务结束后的清理工作：

```yaml
post_cmd:
  - "sudo docker ps -a |grep -w {docker_name} && sudo docker stop {docker_name}; sudo docker rm -f {docker_name} || true"
  - "sudo docker rmi {image_id} || true"
  - "cd {remote_data_path} && ls |grep -v '\\.log$' |xargs rm -rf || true"
```

**常见用途**：
- 停止和删除容器
- 清理临时文件
- 保留日志文件
- 删除镜像（可选）

**4. scp_file - 文件分发列表**

需要从 Azalea 服务器分发到测试节点的文件：

```yaml
scp_file:
  - "/app/script/model_test/nvidia/h20_test/run_test.sh"
  - "/app/script/model_test/nvidia/h20_test/get_progress.sh"
  - "/app/script/model_test/nvidia/h20_test/get_result.py"
```

**注意事项**：
- 必须是绝对路径
- 从 Azalea 容器内的路径
- 会自动分发到 `{remote_data_path}` 目录

**5. params - 参数定义**

固定参数和默认值：

```yaml
params:
  entry_script: run_test.sh
  image_id: nvidia/cuda:12.0-runtime
  default_param1: value1
  query_interval: 1  # 进度查询间隔（分钟）
```

**特殊参数**：
- `entry_script` - 主执行脚本名称
- `query_interval` - 进度查询间隔（分钟）
- 其他参数会传递给脚本

**6. task_timeout - 任务超时**

```yaml
task_timeout: 120  # 单位：分钟
```

- 任务执行的最大时长
- 超时后任务会被标记为失败
- 0 表示不限制超时

**7. task_estimated_time - 预估时长**

```yaml
task_estimated_time: 60  # 单位：分钟
```

- 用于计算预计完成时间
- 仅用于显示，不影响实际执行

**8. result - 结果提取命令**

从日志文件中提取测试结果：

```yaml
result: "py_cmd=$(command -v python || command -v python3); $py_cmd {remote_data_path}/get_result.py --log_file {remote_data_path}/{task_name}_{node_id}_test.log"
```

**要求**：
- 必须输出 JSON 格式
- JSON 的 key 必须与 expected_result 中的 key 对应
- 执行失败时输出空 JSON `{}`

**示例输出**：
```json
{
  "tokens_per_sec": 2156.78,
  "latency_ms": 28.5,
  "throughput": 1024
}
```

**9. progress - 进度查询命令**

查询任务执行进度：

```yaml
progress: "bash {remote_data_path}/get_progress.sh {remote_data_path}/{task_name}_{node_id}_test.log {docker_name} {entry_script}"
```

**输出要求**：
- 正常进度：输出 0-100 的整数
- 任务失败：输出 `exception:错误信息`
- 文件不存在：输出 `exception:log file not found`

**10. download_file - 下载文件列表**

测试完成后可下载的文件：

```yaml
download_file:
  - "{remote_data_path}/{task_name}_{node_id}_test.log"
  - "{remote_data_path}/performance_report.json"
```

#### 变量替换

所有命令中都可以使用以下变量：

| 变量                 | 说明           | 示例                               |
| -------------------- | -------------- | ---------------------------------- |
| `{remote_data_path}` | 远程工作目录   | `/root/azalea_test/task_123`       |
| `{task_name}`        | 任务名称       | `inference_test`                   |
| `{task_id}`          | 任务ID         | `uuid`                             |
| `{node_name}`        | 节点名称       | `gpu-node-01`                      |
| `{node_id}`          | 节点ID         | `uuid`                             |
| `{docker_name}`      | Docker容器名称 | `azalea_NVIDIA_H20_inference_test` |
| `{gpu_manufacturer}` | GPU厂商        | `NVIDIA`                           |
| `{gpu_type}`         | GPU型号        | `H20`                              |
| `{entry_script}`     | 入口脚本名称   | `run_test.sh`                      |
| `{image_id}`         | Docker镜像     | `nvidia/cuda:12.0`                 |
| 自定义参数           | 用户配置的参数 | `{max_batch_size}`                 |

---

## 🎯 最佳实践

### 1. 命名规范

**测试类型命名**：
- 格式：`{operation}_{model}_{variant}`
- 示例：
  - `inference_llama2-70b`
  - `training_gpt3_175b`
  - `finetune_bert_base`

**脚本命名**：
- 主脚本：`run_{test_type}.sh`
- 进度脚本：`get_{test_type}_progress.sh`
- 结果脚本：`get_{test_type}_result.py`

### 2. 目录结构

```
script/model_test/
├── nvidia/
    ├── h20_inference_benchmark_llama2-70b/
        ├── run_inference_benchmark_llama2-70b.sh
        ├── get_inference_benchmark_llama2-70b_progress.sh
        └── get_inference_benchmark_llama2-70b_result.py

```

### 3. 错误处理

**脚本中的错误处理**：
```bash

# 或使用条件判断
if ! command; then
    echo "Test task end failed" >> $LOG_FILE
    exit 1
fi

```

**Python中的错误处理**：
```python
try:
    # 处理逻辑
    result = process_data()
except FileNotFoundError:
    print(json.dumps({}))
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    print(json.dumps({}))
    sys.exit(0)
```

**资源限制**：
```yaml
task_cmd:
  - "sudo docker run --gpus all --cpus=16 --memory=64g ..."
```

### 4. 调试技巧

**启用详细日志**：
```bash
#!/bin/bash
set -x  # 打印执行的命令

# 或者
exec 2>&1 | tee detailed.log
```

**保留中间文件**（调试时）：
```yaml
post_cmd:
  - "echo 'Debug mode: keeping all files'"
  # - "cd {remote_data_path} && rm -rf temp_files"  # 注释掉清理命令
```

---

## ❓ 常见问题

### Q1：如何调试测试任务？

**A：** 有多种调试方法：

**方法1：查看任务日志**
```bash
# 在测试节点上
cat /root/azalea_test/<task_id>/<task_name>_<node_id>_test.log
```

**方法2：查看 Azalea 日志**
```bash
docker logs azalea_app | grep "model_task"
```

---

### Q2：任务一直卡在某个进度怎么办？

**A：** 检查以下几点：

**1. 检查进度查询脚本**
```bash
# 手动执行进度查询脚本
bash get_progress.sh <log_file> <docker_name> <script_name>
```

**2. 检查任务是否真的在运行**
```bash
# 查看容器状态
sudo docker ps | grep <container_name>

# 查看容器进程
sudo docker top <container_name>

# 查看容器日志
sudo docker logs <container_name>
```

**3. 检查日志文件**
```bash
# 实时查看日志
vi /app/pv/logs/azalea.log
```

---

### Q3：如何支持新的 GPU 型号？

**A：** 添加新 GPU 型号的步骤：

**1. 在参数配置中添加**
```json
{
  "your_test": {
    "NVIDIA": {
      "H100": {  // 新GPU型号
        "params": [...],
        "expected_result": [...]
      }
    }
  }
}
```

**2. 在流程配置中添加**
```yaml
your_test:
  NVIDIA:
    H100:  # 新GPU型号
      pre_cmd: [...]
      task_cmd: [...]
      # ... 其他配置
```

**3. 创建对应的测试脚本**
```bash
mkdir -p script/model_test/nvidia/h100_your_test
# 创建测试脚本
```

---

### Q4：如何处理长时间运行的测试？

**A：** 对于长时间测试（如训练任务），注意：

**1. 设置合理的超时时间**
```yaml
task_timeout: 1440  # 24小时，单位：分钟
```

**2. 实现准确的进度计算**
```bash
# 基于epoch数量
total_epochs=100
completed_epochs=$(grep -c "Epoch" $log_file)
progress=$((completed_epochs * 100 / total_epochs))
```

---

### Q5：测试结果对比失败怎么办？

**A：** 检查以下几点：

**1. 确认结果提取正确**
```bash
# 手动执行结果提取脚本
python get_result.py --log_file <log_file>

# 检查输出格式
# 应该是：{"metric_name": value}
```

**2. 确认期望值设置合理**
```json
{
  "expected_result": [
    {
      "key": "tokens_per_sec",  // 必须与结果中的key匹配
      "default_value": 2000,
      "compare": "min"  // 实际值 >= 2000
    }
  ]
}
```

**3. 查看详细对比结果**
```
Web界面 → 模型测试 → 查看结果
会显示：
- 指标名称
- 实际值
- 期望值
- 对比结果（normal/abnormal）
```

---

### Q6：如何适配非 Docker 环境？

**A：** 如果不使用 Docker，可以直接在宿主机执行：

**修改 task_cmd**：
```yaml
task_cmd:
  - "cd {remote_data_path}"
  - "bash {entry_script} {param1} {param2}"
```

**修改 progress 命令**：
```yaml
progress: "bash {remote_data_path}/get_progress.sh {remote_data_path}/test.log 'host' {entry_script}"
```

**修改进度脚本**：
```bash
function is_task_still_running() {
    # 不检查Docker，直接检查进程
    ps aux | grep "$task_script" | grep -v grep &> /dev/null
    return $?
}
```

---

### Q7：如何添加多种测试模式（预训练/推理/微调）？

**A：** 为不同模式创建不同的测试类型：

```json
{
  "training_model_x": {  // 预训练
    "NVIDIA": {
      "H20": {
        "params": [...]
      }
    }
  },
  "inference_model_x": {  // 推理
    "NVIDIA": {
      "H20": {
        "params": [...]
      }
    }
  },
  "finetune_model_x": {  // 微调
    "NVIDIA": {
      "H20": {
        "params": [...]
      }
    }
  }
}
```

每种模式有独立的：
- 参数配置
- 流程配置
- 测试脚本

---

### Q9：如何自定义进度显示？

**A：** 进度查询脚本可以自定义：

**示例1：基于步骤**
```bash
progress=0
grep "Data loading completed" $log_file &> /dev/null && progress=10
grep "Model loading completed" $log_file &> /dev/null && progress=30
grep "Warmup completed" $log_file &> /dev/null && progress=50
grep "Testing started" $log_file &> /dev/null && progress=70
grep "Testing completed" $log_file &> /dev/null && progress=90
echo $progress
```

**示例2：基于百分比**
```bash
# 假设日志中有: Progress: 45%
percent=$(grep -oP 'Progress:\s+\K\d+' $log_file | tail -1)
echo ${percent:-0}
```
---

### Q10：如何添加自定义指标？

**A：** 在结果解析脚本中添加：

**1. 在日志中输出指标**
```bash
echo "[METRIC] custom_metric: 123.45" >> $LOG_FILE
```

**2. 在解析脚本中提取**
```python
def extract_metrics(log_file):
    result_dict = {}
    with open(log_file, 'r') as file:
        for line in file:
            if '[METRIC]' in line:
                match = re.search(r'\[METRIC\]\s+(\w+):\s+([\d.]+)', line)
                if match:
                    key = match.group(1)
                    value = float(match.group(2))
                    result_dict[key] = value
    return result_dict
```

**3. 在期望结果中配置**
```json
{
  "expected_result": [
    {
      "key": "custom_metric",
      "name_zh": "自定义指标",
      "default_value": 100,
      "compare": "min"
    }
  ]
}
```
