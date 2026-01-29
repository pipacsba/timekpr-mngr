# storage.py
"""
Filesystem layout and persistence helpers.

All data for the application lives under DATA_ROOT (default /data).
"""

from pathlib import Path
import json
from typing import Any

import logging 
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Root & directory layout (configurable)
# -------------------------------------------------------------------

DATA_ROOT: Path = Path('/data')  # default, can be overridden from main.py

CACHE_DIR = DATA_ROOT / 'cache'
KEYS_DIR = DATA_ROOT / 'ssh_keys'
PENDING_DIR = DATA_ROOT / 'pending_uploads'
SERVERS_FILE = DATA_ROOT / 'servers.json'
HISTORY_DIR = DATA_ROOT / 'history'
ADDON_CONFIG_FILE = DATA_ROOT / 'options.json'


# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------
def _ensure_dirs() -> None:
    """
    Ensure required directories exist.
    """
    for path in (DATA_ROOT, CACHE_DIR, KEYS_DIR, PENDING_DIR, HISTORY_DIR):
        path.mkdir(parents=True, exist_ok=True)

_ensure_dirs()


# -------------------------------------------------------------------
# History helpers
# -------------------------------------------------------------------
def history_file(server: str, user: str) -> Path:
    return HISTORY_DIR / server / f"{user}.json"


# -------------------------------------------------------------------
# JSON helpers
# -------------------------------------------------------------------
def load_json(path: Path, default: Any):
    if not path.exists():
        logger.warning("No JSON file found")
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("Load JSON file failed")
        return default

def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True))

# -------------------------------------------------------------------
# Cache helpers (used by sync & editor)
# -------------------------------------------------------------------
def server_cache_dir(server_name: str) -> Path:
    path = CACHE_DIR / server_name
    path.mkdir(parents=True, exist_ok=True)
    return path

def user_cache_dir(server_name: str) -> Path:
    path = server_cache_dir(server_name) / 'users'
    path.mkdir(exist_ok=True)
    return path

def stats_cache_dir(server_name: str) -> Path:
    path = server_cache_dir(server_name) / 'stats'
    path.mkdir(exist_ok=True)
    return path

# -------------------------------------------------------------------
# Pending upload helpers
# -------------------------------------------------------------------
def pending_dir(server_name: str) -> Path:
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
# -------------------------------------------------------------------
# Addon config helpers
# -------------------------------------------------------------------
def get_admin_user_list() -> List()
    addon_options=load_json(ADDON_CONFIG_FILE, {})
    try:
        admin_users = addon_options["mqtt"]["server"]
        MQTT_PORT = addon_options["mqtt"]["port"]
        MQTT_BASE = addon_options["mqtt"]["base_topic"]
        MQTT_ENABLED = True
    except:
        MQTT_ENABLED = False
        logger.warning("No MQTT config could be read, disabled")
