# ssh_sync.py
"""
SSH synchronization engine.

Responsibilities:
- Periodically check server availability
- Download server / user / stats configs
- Upload pending user modifications
- Never block the UI
"""

import os
import time
import socket
import hashlib
import paramiko
from pathlib import Path
from typing import Dict

from servers import load_servers, get_remote_paths
from storage import (
    KEYS_DIR,
    PENDING_DIR,
    server_cache_dir,
    user_cache_dir,
    stats_cache_dir,
    pending_dir,
    pending_user_dir,
    pending_stats_dir,
)

import threading
trigger_event = threading.Event()

import logging
logger = logging.getLogger(__name__)
logger.info("ssh_sync module loaded")

#internal variables
class VariableWatcher:
    def __init__(self):
        self._value = True
        self.observers = []

    def set_value(self, new_value : bool):
        self._value = new_value
        self.notify(new_value)

    def get_value(self):
        return self._value

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify(self, new_value):
        for observer in self.observers:
            observer()

class ServersWatcher:
    def __init__(self):
        self._value = []
        self.observers = []

    def set_value(self, new_value):
        self._value = new_value
        self.notify(new_value)

    def get_value(self):
        return self._value

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify(self, new_value):
        for observer in self.observers:
            observer()

    def is_online(self, server_name: str) -> bool:
        return server_name in self._value
        
change_upload_is_pending = VariableWatcher()
servers_online = ServersWatcher()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _tree_has_any_file(directory):
    found = False
    for _, _, files in os.walk(directory):
        if files:
            found = True
    logger.info(f"Finding files in folder: {directory} with result: {found}")
    return found

def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect(server: Dict) -> paramiko.SSHClient | None:
    """
    Create SSH connection or return None if unreachable.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=server["host"],
            port=server.get("port", 22),
            username=server["user"],
            key_filename=str(KEYS_DIR / server["key"]),
            timeout=5,
        )
        return client

    except (socket.error, paramiko.SSHException) as e:
        logger.debug(f"SSH connect failed: {e}")
        return None


def _scp_get_if_changed(sftp, remote: str, local: Path) -> bool:
    """
    Download remote file only if changed.
    Returns True if local file was updated.
    """
    try:
        remote_stat = sftp.stat(remote)
    except FileNotFoundError:
        return False

    local.parent.mkdir(parents=True, exist_ok=True)

    if local.exists():
        local_stat = local.stat()

        # Fast path: same size and timestamp
        if (
            local_stat.st_size == remote_stat.st_size
            and int(local_stat.st_mtime) == int(remote_stat.st_mtime)
        ):
            return False

    tmp = local.with_suffix(local.suffix + ".tmp")

    try:
        sftp.get(remote, str(tmp))
    except Exception as e:
        logger.warning(f"Failed to download {remote}: {e}")
        return False

    if local.exists():
        if _file_hash(tmp) == _file_hash(local):
            tmp.unlink()
            return False

    tmp.replace(local)
    os.utime(local, (remote_stat.st_atime, remote_stat.st_mtime))
    return True


def _scp_put(sftp, local: Path, remote: str) -> bool:
    result = False
    try:
        sftp.put(str(local), remote)
        result = True
    except:
        result = False
    return result

def _ssh_update_allowance(a_client, local: Path) -> bool:
    result = True
    try:
        #sftp.put(str(local), remote)
        logger.info("ssh command execution started")
        text = local.read_text()
        logger.info("ssh command execution started, file is read")
        for raw in text.splitlines():
            command = raw
            logger.info(f"ssh command identified:  {command}")
            stdin, stdout, stderr = a_client.exec_command(command)
            logger.info(f"ssh command returned")
            if (stdout.channel.recv_exit_status() == 0):
                logger.info(f"ssh command returned with not 0 exit code")
                result = (result and True)
            else:
                result = False
    except:
        logger.info("ssh command execution failed, caught by exception handler")
        result = False
    return result


# -------------------------------------------------------------------
# Download logic
# -------------------------------------------------------------------

def sync_from_server(server_name: str, server: Dict) -> bool:
    """
    Pull all known configs from a server.
    Returns True if server was reachable.
    """
    client = _connect(server)
    if not client:
        return False

    try:
        sftp = client.open_sftp()
        paths = get_remote_paths(server_name)

        # --- server config ---
        if "server" in paths:
            updated = _scp_get_if_changed(
                sftp,
                paths["server"],
                server_cache_dir(server_name) / "server.conf",
            )
            if updated:
                logger.info(f"[{server_name}] server.conf updated")

        # --- user configs ---
        for user, remote_path in paths.get("users", {}).items():
            updated = _scp_get_if_changed(
                sftp,
                remote_path,
                user_cache_dir(server_name) / f"{user}.conf",
            )
            if updated:
                logger.info(f"[{server_name}] user {user} config updated")

        # --- stats ---
        for user, remote_path in paths.get("stats", {}).items():
            updated = _scp_get_if_changed(
                sftp,
                remote_path,
                stats_cache_dir(server_name) / f"{user}.stats",
            )
            if updated:
                logger.info(f"[{server_name}] stats for {user} updated")

        return True

    finally:
        client.close()


# -------------------------------------------------------------------
# Upload logic
# -------------------------------------------------------------------

def upload_pending(server_name: str, server: Dict) -> bool:
    """
    Upload pending changes if server is reachable.
    """
    logger.info("ssh upload pending started")
    client = _connect(server)
    success = True
    if not client:
        return False

    try:
        sftp = client.open_sftp()
        paths = get_remote_paths(server_name)

        # --- server config ---
        server_file = pending_dir(server_name) / "server.conf"
        if server_file.exists():
            if _scp_put(sftp, server_file, paths["server"]):
                server_file.unlink()
                logger.info(f"[{server_name}] uploaded server.conf")
            else:
                success = False

        # --- user configs ---
        for file in pending_user_dir(server_name).glob("*.conf"):
            username = file.stem
            remote = paths.get("users", {}).get(username)
            if remote:
                if _scp_put(sftp, file, remote):
                    file.unlink()
                    logger.info(f"[{server_name}] uploaded user {username}")
                else:
                    success = False

        # --- stats ---
        logger.info("ssh upload check for stats file")
        for file in pending_stats_dir(server_name).glob("*.stats"):
            logger.info(f"ssh upload check for stats file passed: {file}")
            username = file.stem
            logger.info(f"ssh upload check for stats file fouind for {server_name} {username}")
            if _ssh_update_allowance(client, file):
                file.unlink()
                logger.info(f"[{server_name}] updated allowance for {username}")
            else:
                logger.info("ssh upload tats file failed")
                success = False
    except:
        success = False

    finally:
        client.close()
        return success


def trigger_ssh_sync():
    logger.info("Manual SSH sync triggered")
    trigger_event.set()


# -------------------------------------------------------------------
# Periodic runner
# -------------------------------------------------------------------
def run_sync_loop_with_stop(stop_event, interval_seconds: int = 180) -> None:
    global change_upload_is_pending
    global servers_online
    logger.info("SSH sync loop started")
    success = True
    online_servers = []

    while not stop_event.is_set():
        servers = load_servers()

        for name, server in servers.items():
            reachable = upload_pending(name, server)
            if reachable:
                online_servers.append(name)
                sync_from_server(name, server)

        servers_online.set_value(online_servers)
        change_upload_is_pending.set_value(_tree_has_any_file(PENDING_DIR))
        # clear trigger before waiting
        trigger_event.clear()

        # wait until either:
        # - interval expires
        # - trigger_event is set
        # - stop_event is set
        triggered = trigger_event.wait(interval_seconds)
