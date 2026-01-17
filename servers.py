# app/servers.py
"""
Server model and CRUD helpers.

This module owns the structure of servers.json and nothing else.
UI code should NEVER manipulate servers.json directly.
"""

from typing import Dict
from storage import SERVERS_FILE, load_json, save_json


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def load_servers() -> Dict:
    """
    Load all server definitions.
    """
    return load_json(SERVERS_FILE, {})


def save_servers(servers: Dict) -> None:
    """
    Persist server definitions.
    """
    save_json(SERVERS_FILE, servers)


def get_server(name: str) -> Dict | None:
    """
    Get a single server by name.
    """
    return load_servers().get(name)


# -------------------------------------------------------------------
# Server CRUD
# -------------------------------------------------------------------

def add_server(
    name: str,
    host: str,
    user: str,
    key: str,
    port: int = 22,
    server_config: str = '/etc/timekpr/server.conf',
) -> None:
    servers = load_servers()

    servers[name] = {
        'host': host,
        'port': port,
        'user': user,
        'key': key,
        'server_config': server_config,
        'users': {},  # populated separately
    }

    save_servers(servers)


def delete_server(name: str) -> None:
    servers = load_servers()
    servers.pop(name, None)
    save_servers(servers)


# -------------------------------------------------------------------
# User management (per server)
# -------------------------------------------------------------------

def add_user(
    server_name: str,
    username: str,
    user_config_path: str,
    stats_path: str,
) -> None:
    servers = load_servers()
    server = servers.get(server_name)

    if not server:
        raise KeyError(f'Server "{server_name}" not found')

    server.setdefault('users', {})[username] = {
        'config': user_config_path,
        'stats': stats_path,
    }

    save_servers(servers)


def delete_user(server_name: str, username: str) -> None:
    servers = load_servers()
    server = servers.get(server_name)

    if not server:
        return

    server.get('users', {}).pop(username, None)
    save_servers(servers)


def list_users(server_name: str) -> Dict:
    server = load_servers().get(server_name, {})
    return server.get('users', {})


# -------------------------------------------------------------------
# Path helpers (used by sync & editor)
# -------------------------------------------------------------------

def get_remote_paths(server_name: str) -> Dict:
    """
    Returns a normalized structure:
    {
        "server": "/path/server.conf",
        "users": { "alice": "/path/alice.conf" },
        "stats": { "alice": "/path/alice.stats" }
    }
    """
    server = get_server(server_name)
    if not server:
        return {}

    return {
        'server': server['server_config'],
        'users': {
            u: v['config']
            for u, v in server.get('users', {}).items()
        },
        'stats': {
            u: v['stats']
            for u, v in server.get('users', {}).items()
        },
    }
