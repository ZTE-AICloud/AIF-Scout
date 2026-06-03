# Azalea Nvidia Runtime容器使用说明

参考命令如下

```shell
docker run -it -d -P --restart=always -e SSH_PORT=2222  --privileged=true --shm-size=64g --gpus all --network host --name azalea_nvidia_runtime --hostname $(hostname)-azalea azalea_nvidia_runtime:0.5
```

基本系统是Ubuntu22.04

支持功能/命令：

- 内置ssh server和client
- 同类容器之间ssh免密访问
- python环境(python3.10)
- cuda运行时(编译后的cuda程序可以运行)
- openmpi工具(4.1.2)
- nccl-tests工具(2.13.6)，工具目录为/workspace/nccl-tests
- gpu-burn工具，工具目录为/workspace/gpu-burn

已安装python关键的包：

- torch
- fire
- numpy
- triton

打包内置的工具

- /workspace/tools目录下
  - h2d.py
  - d2h.py
  - d2d.py
  - membw.py
  - tflops.py

## 构建镜像

1. 拷贝解压nccl-tests.zip(已编译)、gpu-burn.zip(已编译)到本目录下
2. (可选)手动拷贝需要的程序到cache目录，后续会将cache目录拷贝到镜像内的/workspace目录
3. make build
4. (可选)make clean清理cache目录
