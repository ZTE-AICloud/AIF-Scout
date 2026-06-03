# Azalea - 开放型算力基础设施评测框架

<div align="center">

**Azalea** 是由中兴通讯打造的开放型算力基础设施开源评测框架，致力于解决智算中心建设中硬件异构性强、软件兼容性差、软硬集验收效率低三大核心挑战。

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1.9-green.svg)](https://www.djangoproject.com/)

</div>

---

## 📖 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [安装部署](#安装部署)
- [快速开始](#快速开始)
- [API接口文档](#api接口文档)
- [配置说明](#配置说明)
- [许可证](#许可证)
- [贡献指南](#贡献指南)

---

## 🎯 项目简介

Azalea 采用模块化架构设计，从基础检查、性能压测、模型压测等方面入手，为智算服务器集群、RDMA网络提供端到端评测框架。Azalea 适配了多家AI硬件厂商的加速引擎，以更灵活地连接AI硬件与软件生态，为硬件厂商提供评测沙箱环境，加速产品生态适配进程，拓宽评测的边界和效率。

通过开放的插件框架，第三方厂商可以快速地搭建个性化评测系统，帮助他们在智算中心建设硬集/软集阶段快速发现并解决潜在的问题，确保后续训练和推理任务的顺利进行。

### 核心价值

- **解决硬件异构性** - 适配多家AI硬件厂商，统一评测标准
- **提升软件兼容性** - 标准化测试流程，保证软硬件协同
- **提高验收效率** - 自动化批量检测，端到端评测体系

---

## ✨ 核心特性

### 🖥️ 节点管理
- **智能纳管** - 支持单节点添加和批量CSV导入
- **自动识别** - 自动获取节点GPU型号、数量、厂商信息
- **SSH互信** - 自动建立节点间SSH信任关系
- **标签管理** - 灵活的节点标签系统，便于分类管理

### 🔍 环境检测

#### 基础硬件检查
- **CPU检查** - 型号验证、核心数量统计
- **内存检查** - 容量验证、型号识别
- **硬盘检查** - 容量统计、型号识别
- **RAID卡检查** - 型号验证、数量统计

#### GPU深度检查
- **基础信息** - GPU型号、数量、驱动版本验证
- **状态监控** - GPU运行状态实时检测
- **算力测试**
  - BF16算力检测（Brain Floating Point 16）
  - FP32算力检测（32位浮点）
  - INT8算力检测（8位整数）
  - TF32算力检测（TensorFloat-32）
- **带宽测试**
  - D2D（Device to Device）带宽测试
  - H2D（Host to Device）带宽测试
  - D2H（Device to Host）带宽测试
  - GPU显存带宽测试
- **拓扑检查** - GPU拓扑结构一致性验证

#### 网络全面检测
- **网卡检查**
  - 网卡状态检测（速率、MTU配置）
  - 驱动版本验证
  - 光模块健康度检测（功率、温度等）
- **网络连通性**
  - Ping连通性测试
  - RoCE网络通断检查
- **网络性能**
  - 存储带宽测试
  - 参数面网络带宽测试（支持ib_write_bw/ib_send_bw/ib_read_bw）
  - RoCE网络时延测试（支持ib_write_lat/ib_send_lat/ib_read_lat）
- **网卡压测**
  - 参数面网卡长时间打流压测
  - 存储面网卡长时间打流压测
  - RDMA带宽时延性能综合测试（支持n2n/fullmesh/all_n2n/all_fullmesh模式）

#### OS配置检查
- **CPU配置** - CPU空闲状态检查（poll模式）
- **PCIe配置** - PCIe ACS状态检查
- **RoCE配置** - 优先级信任、队列配置、TCP ECN、Traffic Class等

#### PCIe链路检查
- **网卡PCIe** - 网卡PCIe连接状态检查
- **GPU PCIe** - GPU PCIe连接状态检查

#### 集合通信压测
- **多算法支持** - all_reduce、all_gather、all_to_all、reduce_scatter、reduce、broadcast、sendrecv
- **多节点协同** - 支持1-128节点集合通信测试
- **性能分析** - 带宽性能分析、自定义带宽标准值对比

### 🤖 模型测试
- **推理性能测试** - 支持主流大模型推理性能评测（如LLaMA2-70B）
- **多厂商支持** - 适配NVIDIA H20等多种GPU型号
- **灵活配置**
  - 自定义batch_size、输入输出长度
  - 可配置张量并行数
  - Docker容器化部署
- **结果对比** - 实测值与期望值自动对比分析
- **日志管理** - 完整的测试日志下载和查看

### 📁 文件管理
- **文件上传** - 支持大文件分片上传
- **类型分类** - 多种文件类型支持

### 👤 用户系统
- **认证管理** - JWT令牌认证机制
- **权限控制** - 基于Django的权限管理
- **会话管理** - 安全的会话控制和超时机制

---

## 🏗️ 系统架构

```
Azalea
├── Web前端层
│   └── RESTful API接口 + WebSocket实时通信
├── 业务逻辑层
│   ├── 节点管理服务
│   ├── 环境检测服务
│   ├── 模型测试服务
│   ├── 文件管理服务
│   └── 系统管理服务
├── 数据访问层
│   └── Repository模式数据仓库
├── 任务执行层
│   ├── SSH远程执行
│   ├── 并行任务调度
│   └── 状态实时同步
└── 配置管理层
    ├── 检测项配置（JSON）
    ├── 模型测试配置（YAML）
    └── 系统配置
```

### 技术栈

- **后端框架**: Django 5.1.9 + Django REST Framework
- **实时通信**: Django Channels + WebSocket + Redis
- **数据库**: SQLite（可扩展为PostgreSQL/MySQL）
- **任务调度**: 多线程 + 异步任务队列
- **远程执行**: Paramiko SSH + ClusterShell
- **容器化**: Docker + Dockerfile
- **反向代理**: Nginx

---

## 🚀 安装部署

### 环境要求

- Docker 20.10+
- Docker Compose（可选）
- 操作系统：Linux（推荐Ubuntu 22.04）

### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/ZTE-AICloud/AIF-Scout.git
cd AIF-Scout/azalea

# 2. 构建镜像
make imagebuild

# 3. 启动服务
docker run -d \
  --restart=always \
  -p 9001:9001 \
  --name azalea_app \
  azalea_app:v1
```

### 验证安装

```bash
# 检查容器状态
docker ps | grep azalea

# 查看日志
docker logs azalea_app

# 访问Web界面
curl http://localhost:9001
```

---

## 🎬 快速开始

### 1. 访问系统

打开浏览器访问：`http://localhost:9001`

### 2. 首次登录

- 首次访问时输入的用户名和密码将作为管理员账号注册
- 后续使用该账号登录系统

### 3. 添加检测节点

进入 **配置 → 节点管理**

**单节点添加：**
```
IP地址: 192.0.2.100
SSH端口: 22
用户名: root
密码: ******
节点标签: {"rack": "A1"}
```

**批量添加：**
- 下载CSV模板：`etc/template/add_node_template.csv`
- 填写节点信息
- 上传CSV文件

### 4. 执行环境检查

进入 **环境检查 → 基础检查/网络检查**

1. 点击"创建"
2. 填写任务名称
3. 选择检测节点
4. 勾选检测项
5. 设置检测参数（如算力阈值）
6. 点击"确定"创建检查任务
7. 启动创建的检查任务
8. 实时查看检测进度和结果

### 5. 执行模型测试

进入 **模型测试 → 模型测试**

1. 点击"创建"
2. 选择测试类型（如模型推理性能--llama2-70b）
3. 选择测试节点
4. 配置测试参数
5. 点击"确定"创建测试任务
6. 启动创建的测试任务
7. 查看结果

---

## 📚 API接口文档

Azalea 提供完整的 RESTful API 接口，支持系统集成和二次开发。

### 核心功能模块

| 模块         | 功能描述                         | 接口数量 |
| ------------ | -------------------------------- | -------- |
| **系统管理** | 用户认证、密码管理、配置读取     | 4个      |
| **节点管理** | 节点增删改查、批量导入、状态刷新 | 8个      |
| **环境检查** | 检查任务管理、结果查询、日志下载 | 10个     |
| **文件管理** | 文件上传下载、记录管理、MD5校验  | 6个      |
| **模型任务** | 任务创建执行、结果查询和下载     | 8个      |

### 特性说明

- ✅ **完整的接口规范** - 详细的请求/响应参数说明和示例
- ✅ **数据模型定义** - 所有核心数据模型的字段说明
- ✅ **安全机制说明** - JWT认证、密码加密、CSRF保护
- ✅ **WebSocket支持** - 实时消息推送机制
- ✅ **Service层架构** - 清晰的代码架构和层次划分

### 查看完整文档

📖 **[点击查看 API 接口文档](docs/api_guide.md)**

文档包含：
- 所有 REST API 接口的详细说明
- 请求参数和响应格式
- 完整的 JSON 示例
- 数据模型定义
- 错误处理规范
- 认证和安全机制

**基础路径**: `/script/`
**认证方式**: JWT Token
**通信协议**: HTTP/HTTPS + WebSocket

---

## ⚙️ 配置说明

### 环境检测配置

**详细指南：** 请参阅 [环境检测增加检查项指南](docs/add_env_check_item_guide.md)

配置文件位置：`etc/environment_check/`

- `environment_check_item.json` - 检测项定义
- `basic_check_menu.json` - 基础检查菜单
- `network_check_menu.json` - 网络检查菜单

### 模型测试配置

**详细指南：** 请参阅 [模型测试任务配置指南](docs/add_model_task_guide.md)

配置文件位置：`etc/model_testing/`

- `model_testing_configure.yml` - 测试命令和流程配置
- `model_testing_param.json` - 测试参数定义

### 系统配置

配置文件：`etc/azalea.conf.default`


### GPU配置

配置文件：`etc/gpu_pci.json`

定义GPU厂商和型号的PCIe识别信息。

---

## 📄 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源协议。

```
Copyright 2025 ZTE Corporation.
All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 🤝 贡献指南

我们欢迎并感谢所有形式的贡献！

### 如何贡献

1. **Fork 项目**
   ```bash
   git clone https://github.com/ZTE-AICloud/AIF-Scout.git
   cd AIF-Scout/azalea
   git checkout -b feature/your-feature
   ```

2. **提交代码**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature
   ```

3. **发起 Pull Request**
   - 描述你的更改
   - 关联相关Issue
   - 等待代码审查

### 贡献类型

- 🐛 **Bug修复** - 提交Issue描述问题，提供修复PR
- ✨ **新功能** - 提交Issue讨论方案，实现后提交PR
- 📝 **文档改进** - 完善文档、添加示例、修正错误
- 🎨 **代码优化** - 性能优化、代码重构、增强可读性
- 🧪 **测试用例** - 添加单元测试、集成测试

### 开发规范

- 遵循PEP 8编码规范
- 提交信息使用英文，格式：`Type: description`
  - `Add`: 新增功能
  - `Fix`: 修复问题
  - `Update`: 更新功能
  - `Refactor`: 重构代码
  - `Doc`: 文档更新
- 保持代码简洁，注释清晰
- 新增功能需要添加测试用例

### 报告问题

提交Issue时请包含：
- 问题描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（OS、Python版本、Docker版本等）
- 相关日志

---

## 🙏 致谢

感谢所有为Azalea项目做出贡献的开发者和用户！


