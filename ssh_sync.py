# app/ssh_sync.py
"""
SSH synchronization engine.

Responsibilities:
- Periodically check server availability
- Download server / user / stats configs
- Upload pending user modifications
- Never block the UI
"""

import time
import socket
import paramiko
from pathlib import Path
from typing import Dict

from servers import load_servers, get_remote_paths
from storage import (
    KEYS_DIR,
    server_cache_dir,
    user_cache_dir,
    stats_cache_dir,
    pending_dir,
    pending_user_dir,
    pending_stats_dir,
)


# -------------------------------------------------------------------
# SSH helpers
# -------------------------------------------------------------------

def _connect(server: Dict) -> paramiko.SSHClient | None:
    """
    Create SSH connection or return None if unreachable.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=server['host'],
            port=server.get('port', 22),
            username=server['user'],
            key_filename=str(KEYS_DIR / server['key']),
            timeout=5,
        )
        return client

    except (socket.error, paramiko.SSHException):
        return None


def _scp_get(sftp, remote: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    sftp.get(remote, str(local))


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
        if 'server' in paths:
            _scp_get(
                sftp,
                paths['server'],
                server_cache_dir(server_name) / 'server.conf'
            )

        # --- user configs ---
        for user, remote_path in paths.get('users', {}).items():
            _scp_get(
                sftp,
                remote_path,
                user_cache_dir(server_name) / f'{user}.conf'
            )

        # --- stats ---
        for user, remote_path in paths.get('stats', {}).items():
            _scp_get(
                sftp,
                remote_path,
                stats_cache_dir(server_name) / f'{user}.stats'
            )

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
        server_file = pending_dir(server_name) / 'server.conf'
        if server_file.exists():
            _scp_put(sftp, server_file, paths['server'])
            server_file.unlink()

        # --- user configs ---
        for file in pending_user_dir(server_name).glob('*.conf'):
            username = file.stem
            remote = paths.get('users', {}).get(username)
            if remote:
                _scp_put(sftp, file, remote)
                file.unlink()

        # --- stats ---
        for file in pending_stats_dir(server_name).glob('*.stats'):
            username = file.stem
            remote = paths.get('stats', {}).get(username)
            if remote:
                _scp_put(sftp, file, remote)
                file.unlink()

    finally:
        client.close()


# -------------------------------------------------------------------
# Periodic runner
# -------------------------------------------------------------------

def run_sync_loop(interval_seconds: int = 180) -> None:
    """
    Main loop – run in a background thread or NiceGUI task.
    """
    while True:
        servers = load_servers()

        for name, server in servers.items():
            reachable = sync_from_server(name, server)

            if reachable:
                upload_pending(name, server)

        time.sleep(interval_seconds)
