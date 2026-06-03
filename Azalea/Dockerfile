FROM ubuntu:22.04

WORKDIR /app
ARG USER=azalea
ARG USER_UID=1000
ARG USER_GID=1000

COPY . /app

RUN mkdir /home/$USER && \
    mv /app/.ssh /home/$USER && \
    echo "django-insecure-qnh%b0h9d*cgagm5p#09tflazz+s+q#_+plaw#1@_la_#b#+6n" > /home/$USER/secret

RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get clean && apt-get update --fix-missing && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends --no-install-suggests -y vim curl python3 python3-pip openssh-client nginx ipmitool redis && \
    pip --no-cache-dir install --progress-bar off -r /app/requirements.txt && \
    ln -s /usr/bin/python3 /usr/bin/python

RUN addgroup --gid $USER_GID $USER && \
    adduser --uid $USER_UID --ingroup $USER --home /home/$USER --shell /bin/sh --disabled-password $USER && \
    chmod +x /app/start.sh && \
    chmod 600 /home/$USER/.ssh/id_rsa /home/$USER/secret && \
    chmod 644 /home/$USER/.ssh/id_rsa.pub /home/$USER/.ssh/config && \
    chmod 700 /home/$USER/.ssh && \
    chown -R $USER:$USER /app /home/$USER /var/log/nginx

RUN rm -rf /tmp/* /var/tmp/* ~/.cache /app/requirements.txt /app/dev-requirements.txt && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf  ~/.cache/pip && \
    find / -type f -name "*.pyc" -delete && \
    find / -type d -name "__pycache__" -delete && \
    rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/locale/*

USER $USER
EXPOSE 9001
ENTRYPOINT ["/app/start.sh"]
