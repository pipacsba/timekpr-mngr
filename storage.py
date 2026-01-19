# app/storage.py
"""
Filesystem layout and persistence helpers.

All data for the application lives under /Data.
No other module should hardcode paths.
"""

from pathlib import Path
import json
from typing import Any


# -------------------------------------------------------------------
# Root & directory layout
# -------------------------------------------------------------------

DATA_ROOT = Path('/data')

CACHE_DIR = DATA_ROOT / 'cache'
KEYS_DIR = DATA_ROOT / 'ssh_keys'
PENDING_DIR = DATA_ROOT / 'pending_uploads'

SERVERS_FILE = DATA_ROOT / 'servers.json'


# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------

def _ensure_dirs() -> None:
    """
    Ensure required directories exist.
    """
    for path in (DATA_ROOT, CACHE_DIR, KEYS_DIR, PENDING_DIR):
        path.mkdir(parents=True, exist_ok=True)


_ensure_dirs()


# -------------------------------------------------------------------
# JSON helpers
# -------------------------------------------------------------------

def load_json(path: Path, default: Any):
    """
    Load JSON from a file or return default if missing.

    The default is NOT written back automatically.
    """
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        # corrupted JSON -> fail safe
        return default


def save_json(path: Path, data: Any) -> None:
    """
    Save data as pretty-printed JSON.
    """
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


# -------------------------------------------------------------------
# Cache helpers (used by sync & editor)
# -------------------------------------------------------------------

def server_cache_dir(server_name: str) -> Path:
    """
    Returns the base cache directory for a server.
    """
    path = CACHE_DIR / server_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_cache_dir(server_name: str) -> Path:
    """
    Cache directory for user configs.
    """
    path = server_cache_dir(server_name) / 'users'
    path.mkdir(exist_ok=True)
    return path


def stats_cache_dir(server_name: str) -> Path:
    """
    Cache directory for stats files.
    """
    path = server_cache_dir(server_name) / 'stats'
    path.mkdir(exist_ok=True)
    return path


# -------------------------------------------------------------------
# Pending upload helpers
# -------------------------------------------------------------------

def pending_dir(server_name: str) -> Path:
    """
    Pending uploads root for a server.
    """
    path = PENDING_DIR / server_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def pending_user_dir(server_name: str) -> Path:
    path = pending_dir(server_name) / 'users'
    path.mkdir(exist_ok=True)
    return path


def pending_stats_dir(server_name: str) -> Path:
    path = pending_dir(server_name) / 'stats'
    path.mkdir(exist_ok=True)
    return path
