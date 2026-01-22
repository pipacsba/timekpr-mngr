# app/ssh_sync.py
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

import logging
logger = logging.getLogger(__name__)
logger.info("ssh_sync module loaded")

#internal variables
change_upload_is_pending = False

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _tree_has_any_file(directory):
    logger.info(f"Finding files in folder: {directory}")
    for _, _, files in os.walk(directory):
        if files:
            return True
    return False

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


def _scp_put(sftp, local: Path, remote: str) -> None:
    sftp.put(str(local), remote)


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

def upload_pending(server_name: str, server: Dict) -> None:
    """
    Upload pending changes if server is reachable.
    """
    client = _connect(server)
    if not client:
        return

    try:
        sftp = client.open_sftp()
        paths = get_remote_paths(server_name)

        # --- server config ---
        server_file = pending_dir(server_name) / "server.conf"
        if server_file.exists():
            _scp_put(sftp, server_file, paths["server"])
            server_file.unlink()
            logger.info(f"[{server_name}] uploaded server.conf")

        # --- user configs ---
        for file in pending_user_dir(server_name).glob("*.conf"):
            username = file.stem
            remote = paths.get("users", {}).get(username)
            if remote:
                logger.info(f"Trying to upload user config file {file} to server side {remote}")
                _scp_put(sftp, file, remote)
                file.unlink()
                logger.info(f"[{server_name}] uploaded user {username}")

        # --- stats ---
        for file in pending_stats_dir(server_name).glob("*.stats"):
            username = file.stem
            remote = paths.get("stats", {}).get(username)
            if remote:
                logger.info(f"Trying to upload user time file {file} to server side {remote}")
                _scp_put(sftp, file, remote)
                file.unlink()
                logger.info(f"[{server_name}] uploaded stats for {username}")

    finally:
        client.close()


def get_pending_status():
    return change_upload_is_pending

# -------------------------------------------------------------------
# Periodic runner
# -------------------------------------------------------------------
def run_sync_loop_with_stop(stop_event, interval_seconds: int = 180) -> None:
    """
    Stop-aware wrapper for Home Assistant / NiceGUI.
    """
    logger.info("SSH sync loop started")
    
    while not stop_event.is_set():
        servers = load_servers()

        change_upload_is_pending = _tree_has_any_file(PENDING_DIR)

        for name, server in servers.items():
            reachable = sync_from_server(name, server)
            if reachable:
                upload_pending(name, server)

        stop_event.wait(interval_seconds)
