# Azalea API 接口文档

## 文档概述

本文档描述了 Azalea 系统的所有 REST API 接口，包括系统管理、节点管理、环境检查、文件管理和模型任务管理等模块。

**基础路径**: `/script/`

**认证方式**: JWT Token (除登录接口外，其他接口需要在请求头中携带 Token)

**请求头**:
```
Content-Type: application/json
X-CSRFToken: {csrf_token}
```

---

## 目录

1. [系统管理 (System)](#1-系统管理-system)
2. [节点管理 (Node)](#2-节点管理-node)
3. [环境检查 (EnvCheck)](#3-环境检查-envcheck)
4. [文件管理 (File)](#4-文件管理-file)
5. [模型任务 (ModelTask)](#5-模型任务-modeltask)
6. [数据模型](#6-数据模型)

---

## 1. 系统管理 (System)

### 1.1 用户登录

**接口**: `POST /script/login/`

**描述**: 用户登录接口，首次登录时如果系统无用户会自动创建。密码需要加密后传输。

**认证**: 无需认证（公开接口）

**请求参数**:
```json
{
  "username": "string (必填)",
  "password": "string (必填)"
}
```

**密码强度要求**（首次创建用户时）:
- 至少8个字符
- 包含大写字母
- 包含小写字母
- 包含数字
- 包含特殊字符

**响应示例**:
```json
{
  "status": "success",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "csrfToken": "csrf_token_string",
}
```

**错误响应**:
```json
{
  "error": "Invalid credentials"
}
```

---

### 1.2 用户登出

**接口**: `GET /script/logout/`

**描述**: 用户登出接口

**请求参数**: 无

**响应示例**:
```json
{
  "status": "success"
}
```

---

### 1.3 修改密码

**接口**: `POST /script/change_password/`

**描述**: 修改当前登录用户的密码

**请求参数**:
```json
{
  "old_password": "string (必填)",
  "new_password": "string (必填)"
}
```

**密码强度要求**:
- 至少8个字符
- 包含大写字母
- 包含小写字母
- 包含数字
- 包含特殊字符
- 新旧密码不能相同

**响应示例**:
```json
{
  "status": "success"
}
```

**注意**: 修改密码成功后会自动登出

---

### 1.4 获取配置文件内容

**接口**: `POST /script/fileConfig/`

**描述**: 从服务器指定配置文件读取内容

**请求参数**:
```json
{
  "file": "string (必填, 配置文件名)"
}
```

**响应示例**:
```json
{
  "configContent": "文件内容字符串"
}
```

---

## 2. 节点管理 (Node)

### 2.1 获取节点列表

**接口**: `GET /script/nodes/`

**描述**: 获取所有节点信息列表

**查询参数**:
- `normal` (可选): `"true"` - 只返回正常可访问的节点

**响应示例**:
```json
{
  "nodes": [
    {
      "id": "uuid-string",
      "node_name": "node-01",
      "username": "root",
      "ip_address": "192.168.1.100",
      "port": 22,
      "node_label": {
        "env": "production",
        "role": "worker"
      },
      "gpu_manufacturer": "NVIDIA",
      "gpu_type": "H20",
      "gpu_count": 8,
      "error_message": "",
      "is_accessible": true,
      "created_at": "2025-11-20T10:00:00Z"
    }
  ]
}
```

---

### 2.2 获取单个节点信息

**接口**: `GET /script/nodes/get/{id}/`

**描述**: 根据节点ID获取节点详细信息

**路径参数**:
- `id`: 节点UUID

**响应示例**:
```json
{
  "id": "uuid-string",
  "node_name": "node-01",
  "username": "root",
  "ip_address": "192.168.1.100",
  "port": 22,
  "node_label": {
    "env": "production"
  },
  "gpu_manufacturer": "NVIDIA",
  "gpu_type": "H20",
  "gpu_count": 8,
  "error_message": "",
  "is_accessible": true,
  "created_at": "2025-11-20T10:00:00Z"
}
```

---

### 2.3 添加单个节点

**接口**: `POST /script/nodes/add/`

**描述**: 添加单个节点，系统会自动通过SSH连接获取节点信息

**请求参数**:
```json
{
  "ip_address": "string (必填, IP地址)",
  "port": "integer (可选, 默认22)",
  "username": "string (必填, SSH用户名)",
  "ssh_password": "string (必填)",
  "node_label": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

**节点标签限制**:
- 最多20个标签
- 键和值必须是字符串
- 键和值长度不超过64字符

**响应示例**:
```json
{
  "node_id": "uuid-string"
}
```

---

### 2.4 批量导入节点

**接口**: `POST /script/nodes/batch_add/`

**描述**: 通过CSV文件批量导入节点，异步处理，结果通过WebSocket推送

**请求类型**: `multipart/form-data`

**请求参数**:
- `file`: CSV文件

**CSV文件格式**:
```csv
ip地址,ssh端口,ssh用户名,ssh密码,节点标签
192.168.1.100,22,root,***,"{\"env\":\"prod\"}"
192.168.1.101,22,root,***,"{\"env\":\"test\"}"
```

**响应示例**:
```json
{
  "message": "Processing started"
}
```

**WebSocket 推送消息** (发送到 `node_manage_group`):
```json
{
  "type": "upload",
  "status": "Success",
  "message": "all 10 nodes added successfully."
}
```

或失败消息：
```json
{
  "type": "upload",
  "status": "Failed",
  "message": "8 nodes added successfully, 2 nodes failed."
}
```

---

### 2.5 修改节点标签

**接口**: `POST /script/nodes/modifyLabel/{id}/`

**描述**: 修改节点的标签信息

**路径参数**:
- `id`: 节点UUID

**请求参数**:
```json
{
  "node_label": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

**响应示例**:
```json
{
  "message": "node modify successfully"
}
```

---

### 2.6 修改节点认证信息

**接口**: `POST /script/nodes/modifyAuth/{id}/`

**描述**: 修改节点的SSH认证信息（用户名、密码、端口），修改后会重新获取节点信息

**路径参数**:
- `id`: 节点UUID

**请求参数**:
```json
{
  "username": "string (必填)",
  "ssh_password": "string (必填)",
  "port": "integer (可选, 默认22)"
}
```

**响应示例**:
```json
{
  "status": "success"
}
```

---

### 2.7 批量删除节点

**接口**: `POST /script/nodes/batch_delete/`

**描述**: 批量删除节点

**请求参数**:
```json
{
  "node_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**响应示例**:
```json
{
  "message": "delete nodes successfully"
}
```

---

### 2.8 批量刷新节点状态

**接口**: `POST /script/nodes/batch_refresh/`

**描述**: 批量刷新节点状态，异步执行，结果通过WebSocket推送

**请求参数**:
```json
{
  "node_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**响应示例**:
```json
{
  "message": "Processing started"
}
```

**WebSocket 推送消息** (发送到 `node_manage_group`):
```json
{
  "type": "refresh",
  "status": "Success",
  "message": "all nodes status refresh"
}
```

---

## 3. 环境检查 (EnvCheck)

### 3.1 获取检查任务列表

**接口**: `GET /script/env_check/tasks/`

**描述**: 获取所有环境检查任务列表

**查询参数**:
- `task_type` (可选): 按任务类型过滤

**响应示例**:
```json
[
  {
    "task_id": "uuid-string",
    "task_name": "GPU_Check",
    "task_type": "basic",
    "status": "success",
    "msg": "",
    "start_time": "2025-11-20T10:00:00Z",
    "end_time": "2025-11-20T10:05:00Z",
    "updated_at": "2025-11-20T10:05:00Z"
  }
]
```

---

### 3.2 获取单个检查任务

**接口**: `GET /script/env_check/tasks/{task_id}`

**描述**: 获取单个检查任务的详细信息，包含检查项和节点信息

**路径参数**:
- `task_id`: 任务UUID

**响应示例**:
```json
{
  "task_id": "uuid-string",
  "task_name": "GPU_Check",
  "task_type": "basic",
  "status": "success",
  "msg": "",
  "start_time": "2025-11-20T10:00:00Z",
  "end_time": "2025-11-20T10:05:00Z",
  "updated_at": "2025-11-20T10:05:00Z",
  "items": [
    {
      "item_id": "uuid",
      "parent": "gpu_check",
      "check_item": "gpu_state_check",
      "param": {"memory_used": "100"},
      "status": "success",
      "msg": "",
      "start_time": "2025-11-20T10:00:00Z",
      "end_time": "2025-11-20T10:01:00Z"
    }
  ],
  "nodes": [
    {
      "node_id": "node-uuid",
      "status": "success",
      "msg": "",
      "start_time": "2025-11-20T10:00:00Z",
      "end_time": "2025-11-20T10:05:00Z"
    }
  ]
}
```

---

### 3.3 创建检查任务

**接口**: `POST /script/env_check/tasks/create/`

**描述**: 创建新的环境检查任务

**请求参数**:
```json
{
  "task_name": "string (必填, 任务名称)",
  "task_type": "basic (必填, basic:基础检测类型；network:网络相关检查类型)",
  "nodes": ["node-uuid1", "node-uuid2"],
  "check_items": [
    {
      "parent": "gpu_check",
      "check_item": "gpu_state_check",
      "param": {"memory_used": "100"}
    }
  ]
}
```

**响应示例**:
```json
{
  "task_id": "uuid-string"
}
```

---

### 3.4 修改检查任务

**接口**: `POST /script/env_check/tasks/modify/{task_id}`

**描述**: 修改已存在的检查任务

**路径参数**:
- `task_id`: 任务UUID

**请求参数**:
```json
{
  "items": [
    {
      "item_id": "uuid",
      "parent": "gpu_check",
      "check_item":"gpu_state_check",
      "param": {"memory_used": "100"}
    }
  ]
}
```

**响应示例**:
```json
{
  "message": "modify task successfully."
}
```

---

### 3.5 执行检查任务

**接口**: `POST /script/env_check/tasks/execute/{task_id}`

**描述**: 执行环境检查任务

**路径参数**:
- `task_id`: 任务UUID

**请求参数**: 无

**响应示例**:
```json
{
  "message": "Execute task successfully."
}
```

---

### 3.6 停止检查任务

**接口**: `POST /script/env_check/tasks/stop/{task_id}`

**描述**: 停止正在执行的检查任务

**路径参数**:
- `task_id`: 任务UUID

**请求参数**: 无

**响应示例**:
```json
{
  "message": "Check task is stopping."
}
```

---

### 3.7 删除检查任务

**接口**: `POST /script/env_check/tasks/delete/`

**描述**: 批量删除检查任务（不能删除运行中的任务）

**请求参数**:
```json
{
  "task_ids": ["uuid1", "uuid2"]
}
```

**响应示例**:
```json
{
  "message": "Check tasks are deleted successfully"
}
```

---

### 3.8 获取检查项结果

**接口**: `GET /script/env_check/task/{task_id}/items/{item_id}/result/`

**描述**: 获取某个检查项在所有节点上的执行结果

**路径参数**:
- `task_id`: 任务UUID
- `item_id`: 检查项UUID

**响应示例**:
```json
{
  "results": [
    {
      "nodes": ["node-uuid1", "node-uuid2"],
      "status": "success",
      "start_time": "2025-11-20T10:00:00Z",
      "end_time": "2025-11-20T10:01:00Z",
      "msg": "",
      "detail_result": [
        "GPU0-->memory used:0 MiB,process:None",
        "GPU1-->memory used:0 MiB,process:None",
        "GPU2-->memory used:0 MiB,process:None",
        "GPU3-->memory used:0 MiB,process:None",
        "GPU4-->memory used:0 MiB,process:None",
        "GPU5-->memory used:0 MiB,process:None",
        "GPU6-->memory used:0 MiB,process:None",
        "GPU7-->memory used:0 MiB,process:None",
      ],
      "format_result": []
    }
  ]
}
```

---

### 3.9 获取节点检查结果

**接口**: `GET /script/env_check/task/{task_id}/node/{node_id}/result/`

**描述**: 获取某个节点在任务中所有检查项的执行结果

**路径参数**:
- `task_id`: 任务UUID
- `node_id`: 节点UUID

**响应示例**:
```json
{
  "items": [
    {
      "parent": "gpu_check",
      "check_item": "gpu_state_check",
      "param": {"memory_used": "100"},
      "status": "success",
      "start_time": "2025-11-20T10:00:00Z",
      "end_time": "2025-11-20T10:01:00Z",
      "msg": "",
      "detail_result": [
        "GPU0-->memory used:0 MiB,process:None",
        "GPU1-->memory used:0 MiB,process:None",
        "GPU2-->memory used:0 MiB,process:None",
        "GPU3-->memory used:0 MiB,process:None",
        "GPU4-->memory used:0 MiB,process:None",
        "GPU5-->memory used:0 MiB,process:None",
        "GPU6-->memory used:0 MiB,process:None",
        "GPU7-->memory used:0 MiB,process:None",
      ],
      "format_result": []
    }
  ]
}
```

---

### 3.10 下载检查日志

**接口**: `POST /script/env_check/tasks/log_download/`

**描述**: 下载环境检查任务的执行日志（ZIP格式）

**请求参数**:
```json
{
  "task_id": "uuid-string"
}
```

**响应**: 文件流（ZIP压缩包）

**响应头**:
```
Content-Type: application/zip
Content-Disposition: attachment; filename="{task_name}_{timestamp}.zip"
```

---

## 4. 文件管理 (File)

### 4.1 获取文件列表

**接口**: `GET /script/files/`

**描述**: 获取所有文件记录列表

**请求参数**: 无

**响应示例**:
```json
{
  "files": [
    {
      "id": "uuid-string",
      "file_type": "common_file",
      "file_name": "dataset.zip",
      "description": "训练数据集",
      "file_size": 1048576,
      "status": "uploaded",
      "additional_info": [
        {
          "md5_checksum": "abc123def456..."
        }
      ],
      "created_at": "2025-11-20T10:00:00Z",
      "updated_at": "2025-11-20T10:05:00Z"
    }
  ]
}
```

**文件类型**:
- `common_file`: 普通文件
- `tool_file`: 工具文件
- `model_file`: 模型文件

**文件状态**:
- `uploading`: 上传中
- `uploaded`: 已上传

---

### 4.2 获取文件信息

**接口**: `GET /script/files/get/{id}/`

**描述**: 获取单个文件的详细信息

**路径参数**:
- `id`: 文件UUID

**响应示例**:
```json
{
  "file": {
    "id": "uuid-string",
    "file_type": "common_file",
    "file_name": "dataset.zip",
    "description": "训练数据集",
    "file_size": 1048576,
    "status": "uploaded",
    "additional_info": [
      {
        "md5_checksum": "abc123def456..."
      }
    ],
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:05:00Z"
  }
}
```

---

### 4.3 创建文件记录

**接口**: `POST /script/files/add/`

**描述**: 创建文件记录（不上传文件内容）

**请求参数**:
```json
{
  "file_name": "string (必填, 文件名)",
  "file_type": "string (必填, 文件类型: common_file/tool_file/model_file)",
  "description": "string (可选, 文件描述)"
}
```

**响应示例**:
```json
{
  "file": {
    "id": "uuid-string",
    "file_type": "common_file",
    "file_name": "dataset.zip",
    "description": "训练数据集",
    "file_size": 0,
    "status": "uploading",
    "additional_info": [],
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:00:00Z"
  }
}
```

---

### 4.4 上传文件

**接口**: `POST /script/files/upload/{id}/`

**描述**: 上传文件内容到已创建的文件记录

**请求类型**: `multipart/form-data`

**路径参数**:
- `id`: 文件记录UUID

**请求参数**:
- `file`: 文件内容

**响应示例**:
```json
{
  "message": "File uploaded successfully",
  "file": {
    "id": "uuid-string",
    "file_type": "common_file",
    "file_name": "dataset.zip",
    "description": "训练数据集",
    "file_size": 1048576,
    "status": "uploaded",
    "additional_info": [
      {
        "md5_checksum": "abc123def456..."
      }
    ],
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:05:00Z"
  }
}
```

**文件存储路径**:
- `common_file`: `PathConfig.UPLOAD_COMMON_FILE_PATH`
- `tool_file`: `PathConfig.UPLOAD_TOOL_FILE_PATH`
- `model_file`: `PathConfig.UPLOAD_MODEL_FILE_PATH`

---

### 4.5 编辑文件记录

**接口**: `POST /script/files/edit/{id}/`

**描述**: 编辑文件记录的描述和类型

**路径参数**:
- `id`: 文件UUID

**请求参数**:
```json
{
  "description": "string (可选, 新的描述)",
  "file_type": "string (可选, 新的文件类型)"
}
```

**响应示例**:
```json
{
  "message": "File edit successfully",
  "file": {
    "id": "uuid-string",
    "file_type": "model_file",
    "file_name": "dataset.zip",
    "description": "更新后的描述",
    "file_size": 1048576,
    "status": "uploaded",
    "additional_info": [
      {
        "md5_checksum": "abc123def456..."
      }
    ],
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:10:00Z"
  }
}
```

---

### 4.6 删除文件记录

**接口**: `POST /script/files/delete/{id}/`

**描述**: 删除文件记录及其关联的文件

**路径参数**:
- `id`: 文件UUID

**请求参数**: 无

**响应示例**:
```json
{
  "message": "File deleted successfully"
}
```

---

## 5. 模型任务 (ModelTask)

### 5.1 获取模型任务列表

**接口**: `GET /script/modelTask/list/`

**描述**: 获取所有模型任务列表

**请求参数**: 无

**响应示例**:
```json
[
  {
    "task_id": "uuid-string",
    "task_name": "inference_test",
    "task_type": "inference_llama2-70b",
    "remote_data_path": "/home/workspace",
    "status": "success",
    "start_time": "2025-11-20T10:00:00Z",
    "end_time": "2025-11-20T15:00:00Z",
    "updated_at": "2025-11-20T15:00:00Z",
    "node_infos": [
      {
        "task_type": "training",
        "node_name": "node-01",
        "node_id": "node-uuid",
        "gpu_manufacturer": "NVIDIA",
        "gpu_type": "H20",
        "gpu_count": 8,
        "status": "success",
        "progress": 100,
        "msg": "",
        "start_time": "2025-11-20T10:00:00Z",
        "end_time": "2025-11-20T15:00:00Z",
        "estimated_end_time": "2025-11-20T15:00:00Z",
        "target_result": {"latency":{"max":600}},
        "task_result": {},
        "task_param": {"dtype":"float16"}
      }
    ]
  }
]
```

**任务状态**:
- `accepted`: 已接受
- `preparing`: 准备中
- `executing`: 执行中
- `success`: 成功
- `failed`: 失败
- `stopping`: 停止中
- `stopped`: 已停止

---

### 5.2 获取单个模型任务

**接口**: `GET /script/modelTask/detail/{task_id}`

**描述**: 获取单个模型任务的详细信息

**路径参数**:
- `task_id`: 任务UUID

**响应示例**:
```json
{
  "task_id": "uuid-string",
  "task_name": "inference_test",
  "task_type": "inference_llama2-70b",
  "remote_data_path": "/home/workspace",
  "status": "success",
  "start_time": "2025-11-20T10:00:00Z",
  "end_time": "2025-11-20T15:00:00Z",
  "updated_at": "2025-11-20T15:00:00Z",
  "node_infos": [
    {
      "task_type": "training",
      "node_name": "node-01",
      "node_id": "node-uuid",
      "gpu_manufacturer": "NVIDIA",
      "gpu_type": "H20",
      "gpu_count": 8,
      "status": "success",
      "progress": 100,
      "msg": "",
      "start_time": "2025-11-20T10:00:00Z",
      "end_time": "2025-11-20T15:00:00Z",
      "estimated_end_time": "2025-11-20T15:00:00Z",
      "target_result": {"latency":{"max":600}},
      "task_result": {},
      "task_param": {"dtype":"float16"}
    }
  ]
}
```

---

### 5.3 创建模型任务

**接口**: `POST /script/modelTask/create/`

**描述**: 创建新的模型任务

**请求参数**:
```json
{
  "task_name": "string (必填, 任务名称)",
  "task_type": "string (必填, 任务类型)",
  "remote_data_path": "string (可选, 远程数据路径)",
  "nodes": ["node-uuid1", "node-uuid2"],
  "task_params": {"dtype":"float16"}
}
```

**响应示例**:
```json
{
  "task_id": "uuid-string"
}
```

---

### 5.4 执行模型任务

**接口**: `POST /script/modelTask/execute/`

**描述**: 执行已创建的模型任务

**请求参数**:
```json
{
  "task_id": "uuid-string (必填)",
  "task_params": {"dtype":"float16"}
}
```

**响应示例**:
```json
{
  "task_id": "uuid-string"
}
```

---

### 5.5 停止模型任务

**接口**: `POST /script/modelTask/stop/`

**描述**: 停止正在执行的模型任务

**请求参数**:
```json
{
  "task_id": "uuid-string (必填)"
}
```

**响应示例**:
```json
{
  "message": "Model task is stopping."
}
```

---

### 5.6 删除模型任务

**接口**: `POST /script/modelTask/delete/`

**描述**: 批量删除模型任务（不能删除运行中的任务）

**请求参数**:
```json
{
  "task_ids": ["uuid1", "uuid2"]
}
```

**响应示例**:
```json
{
  "message": "Model tasks are deleted successfully"
}
```

---

### 5.7 下载任务结果

**接口**: `POST /script/modelTask/download_result/`

**描述**: 下载模型任务的执行结果（ZIP格式）

**请求参数**:
```json
{
  "task_id": "uuid-string (必填)",
  "node_ids": ["node-uuid1", "node-uuid2"]
}
```

**响应**: 文件流（ZIP压缩包）

**响应头**:
```
Content-Type: application/zip
Content-Disposition: attachment; filename="{task_name}_{timestamp}.zip"
```

---

### 5.8 查看任务结果

**接口**: `POST /script/modelTask/view_result/`

**描述**: 在线查看任务执行日志（最后1000行）

**请求参数**:
```json
{
  "task_id": "uuid-string (必填)",
  "node_id": "node-uuid (必填)"
}
```

**响应示例**:
```json
{
  "result": "Epoch 1/100\nLoss: 0.5\nAccuracy: 0.85\n..."
}
```

---

## 7. 错误处理

所有接口统一使用以下错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

常见HTTP状态码：
- `200`: 成功
- `202`: 已接受（异步任务）
- `400`: 请求参数错误
- `401`: 未授权（未登录或Token过期）
- `403`: 禁止访问（权限不足）
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 8. WebSocket 推送

系统使用 WebSocket 进行实时消息推送，主要用于异步任务的状态更新。

**WebSocket 分组**:
- `node_manage_group`: 节点管理相关消息

**消息格式**:
```json
{
  "type": "string (消息类型: upload/refresh)",
  "status": "string (状态: Success/Failed/Error)",
  "message": "string (消息内容)"
}
```

---

## 9. 安全说明

### 9.1 账户锁定

登录失败多次后账户会被锁定30分钟，使用 `django-axes` 实现。

### 9.2 CSRF 保护

除登录接口外，所有POST请求需要携带CSRF Token。

### 9.3 密码强度要求

- 至少8个字符
- 包含大写字母
- 包含小写字母
- 包含数字
- 包含特殊字符

---

## 10. 附录

### 10.1 任务状态枚举

```python
TASK_STATUS_CHOICES = [
    ('accepted', 'Accepted'),
    ('preparing', 'Preparing'),
    ('executing', 'Executing'),
    ('success', 'Success'),
    ('failed', 'Failed'),
    ('stopping', 'Stopping'),
    ('stopped', 'Stopped'),
]
```

### 10.2 文件类型枚举

```python
FILE_TYPE_CHOICES = [
    ('common_file', 'Common File'),
    ('tool_file', 'Tool File'),
    ('model_file', 'Model File'),
]
```

### 10.3 文件状态枚举

```python
FILE_MANAGE_STATUS_CHOICES = [
    ('uploading', 'Uploading'),
    ('uploaded', 'Uploaded'),
]
```
