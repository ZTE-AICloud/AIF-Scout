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

from dataclasses import dataclass

import functools
import logging
import paramiko
import subprocess
from typing import Dict
from typing import List
from typing import Tuple


from pssh.clients.ssh import SSHClient
from pssh.clients.ssh import ParallelSSHClient

# For the latest version of SSH server, the native SSH client now exclusively
# supports password authentication method. Attempting private key authentication
# will result in an error.
from pssh.clients.native import SSHClient as NativeSSHClient
from pssh.clients.native import ParallelSSHClient as NativeParallelSSHClient
from pssh.output import HostOutput
from pssh.config import HostConfig
import pssh.exceptions as pssh_e

from gevent import joinall

from utils.consts import PathConfig


POLICY = paramiko.AutoAddPolicy()

logger = logging.getLogger(__name__)
RecordProcess: Dict[int, subprocess.Popen] = {}


class Common_SSH_Exception(Exception):
    pass


_COMMON_PSSH_EXCEPTION = (
    pssh_e.AuthenticationError,
    pssh_e.HostArgumentError,
    pssh_e.HostConfigError,
    pssh_e.NoIPv6AddressFoundError,
    pssh_e.PKeyFileError,
    pssh_e.ProxyError,
    pssh_e.SCPError,
    pssh_e.SessionError,
    pssh_e.SFTPError,
    pssh_e.SFTPIOError,
    pssh_e.ShellError,
    pssh_e.SSHError,
    pssh_e.Timeout,
    pssh_e.UnknownHostError,
    pssh_e.ConnectionError,
)


def ssh_exception_converter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except _COMMON_PSSH_EXCEPTION as e:
            raise Common_SSH_Exception(str(e))

    return wrapper


@dataclass
class HostOutputData:
    host: str
    exit_code: int
    std_out: List[str]
    std_err: List[str]


@ssh_exception_converter
def copy_file_to_single_node(
    remote_user,
    remote_host,
    remote_password,
    local_path,
    remote_path,
    private_key_path=PathConfig.PRIVATE_KEY_PATH,
    port=22,
    recurse: bool = False,
):
    with NativeSSHClient(
        host=remote_host, user=remote_user, allow_agent=False, password=remote_password, port=port
    ) as client:
        client.copy_file(local_file=local_path,
                         remote_file=remote_path, recurse=recurse)


@ssh_exception_converter
def copy_file_from_single_node_to_local(
    remote_user,
    remote_host,
    remote_password,
    remote_path,
    local_path,
    private_key_path=PathConfig.PRIVATE_KEY_PATH,
    port=22,
):
    with NativeSSHClient(
        host=remote_host, user=remote_user, allow_agent=False, password=remote_password, port=port
    ) as client:
        client.copy_remote_file(remote_file=remote_path, local_file=local_path)


@ssh_exception_converter
def exec_cmd_on_single_host(
    remote_user,
    remote_host,
    remote_password,
    cmd,
    private_key_path=PathConfig.PRIVATE_KEY_PATH,
    port=22,
    use_pty: bool = False,
    timeout=None
) -> HostOutputData:
    """
    Execute a command on multiple hosts using SSH.

    Args:
        remote_user (str): hostname
        remote_host (str): hostname or IP address.
        remote_password (str): hostname password
        cmd (str): Command to be executed on the hosts.
        emulation. Defaults to ``False``.
        private_key_path: Path to the private key for authentication.
        port (int): host port
        use_pty (bool): (Optional) Enable/Disable use of pseudo terminal
        timeout (int | None): Timeout value for the command execution.

    Returns:
        HostOutputData: HostOutputData objects containing output data from each host.

    """

    with SSHClient(host=remote_host, user=remote_user, allow_agent=False,
                   password=remote_password, port=port, num_retries=1,
                   timeout=timeout) as client:
        host_out: HostOutput = client.run_command(
            cmd, use_pty=use_pty)  # timeout=timeout
        err_info = []
        out_info = []
        for err in host_out.stderr:
            err_info.append(str(err))
        for std in host_out.stdout:
            out_info.append(str(std))
        result = HostOutputData(host=host_out.host,
                                exit_code=host_out.exit_code,
                                std_out=out_info,
                                std_err=err_info,
                                )
    return result


# 返回一个生成器，不用等待全部执行结束，调用方通过遍历实时获取执行的结果
# use_pty 开启可以防止SSH会话的stdout/stderr缓冲没有被刷新时挂住
# 类似使用ssh命令的-t选项来强制分配一个伪终端，这样可以确保stdout/stderr的缓冲行为符合预期。
@ssh_exception_converter
def exec_cmd_on_multi_hosts_realtime(
    hosts: List[str],  # list of hostname or ip_address
    host_config: List[HostConfig],
    cmd: str,
    host_args: List[str] | Tuple[str] = None,
    use_pty: bool = False,
    timeout: int | None = None,
    private_key_path=PathConfig.PRIVATE_KEY_PATH,
    stop_on_errors: bool = True
) -> List[HostOutput]:
    """
    Execute a command on multiple hosts using SSH.

    Args:
        hosts (List[str]): List of hostname or IP address.
        host_config (List[HostConfig]): List of host configurations.
        cmd (str): Command to be executed on the hosts.
        host_args (list): As a command completion to support different commands.
        use_pty (bool): (Optional) Enable/Disable use of pseudo terminal
        emulation. Defaults to ``False``.
        timeout (int | None): Timeout value for the command execution.
        private_key_path: Path to the private key for authentication.

    Returns:
        List[HostOutput].
    """
    client = ParallelSSHClient(
        hosts, host_config=host_config, allow_agent=False, num_retries=1)
    output: List[HostOutput] = client.run_command(
        cmd, host_args=host_args, use_pty=use_pty, stop_on_errors=stop_on_errors)
    client.join(timeout=timeout)
    return output


@ssh_exception_converter
def copy_file_to_multi_hosts(
    hosts: List[str],  # list of hostname or ip_address
    host_config: List[HostConfig],
    local_path: str,
    remote_path: str,
    timeout=None,
    raise_error: bool = True,
    recurse: bool = False,
):
    client = NativeParallelSSHClient(
        hosts, host_config=host_config, num_retries=1)
    cmds = client.copy_file(local_file=local_path,
                            remote_file=remote_path, recurse=recurse)
    joinall(cmds, raise_error=raise_error)


def execute_commands_on_host(host, username, password, port, commands, exec_timeout):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(POLICY)
    try:
        try:
            ssh.connect(host, port=port, username=username, password=password)
            for command in commands:
                stdin, stdout, stderr = ssh.exec_command(
                    command, timeout=exec_timeout)
                output = stdout.read().decode("utf-8")
                error = stderr.read().decode("utf-8")
                logger.info(f"Host: {host}, Command: {command}")
                if output:
                    logger.info(f"Output: {output}")
                if error:
                    logger.error(f"Error: {error}")
        except Exception as e:
            logger.error(
                f"Failed to connect or execute command on {host}: {e}")
            raise e
    finally:
        ssh.close()
