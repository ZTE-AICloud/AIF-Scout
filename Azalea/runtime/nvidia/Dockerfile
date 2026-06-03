FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

RUN mkdir -p /workspace /var/run/sshd /root/.ssh && \
    apt-get clean && \
COPY cache /workspace

RUN cp /workspace/utils/start_sshd.sh /workspace/start_sshd.sh && \
    cp /workspace/utils/id_rsa /root/.ssh/id_rsa && \
    cp /workspace/utils/id_rsa.pub /root/.ssh/authorized_keys && \
    cp /workspace/utils/id_rsa.pub /root/.ssh/id_rsa.pub && \
    cp /workspace/utils/ssh_config /root/.ssh/config && \
    rm -rf /workspace/utils

RUN apt-get update --fix-missing \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y vim python3-dev python3-pip openssh-client openssh-server net-tools sshpass iproute2 zip perftest openmpi-bin openmpi-common libopenmpi-dev ethtool iputils-ping strace rdma-core lsscsi \
    && echo 'root:azalea_tool' | chpasswd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && echo 'Port 2222' >> /etc/ssh/sshd_config \
    && ln -s /usr/bin/python3 /usr/bin/python

RUN chmod 600 /root/.ssh/id_rsa && \
    chmod 600 /root/.ssh/authorized_keys && \
    chmod 700 /root/.ssh && \
    chmod 644 /root/.ssh/config && \
    chmod +x /workspace/start_sshd.sh

RUN pip config --user set global.progress_bar off \
    && python3 -m pip --no-cache-dir install numpy triton==3.1.0 torch fire psutil

RUN apt-get clean && \
    rm -rf ~/.cache/pip /tmp/* /var/tmp/*

ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

EXPOSE 2222

CMD ["/workspace/start_sshd.sh"]
