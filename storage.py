# storage.py
"""
Filesystem layout and persistence helpers.

All data for the application lives under DATA_ROOT (default /data).
"""

import os
from pathlib import Path
import json
from typing import Any
import zipfile

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
BACKUP_FILE = DATA_ROOT / 'backup.zip'

CHANNEL = os.getenv("TIMEKPR_MNGR_CHANNEL", "unknown").lower()
IS_EDGE = CHANNEL in ("edge", "unstable", "dev")

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------
def _ensure_dirs() -> None:
    """
    Ensure required directories exist.
    """
    for path in (DATA_ROOT, CACHE_DIR, KEYS_DIR, PENDING_DIR, HISTORY_DIR):
        path.mkdir(parents=True, exist_ok=True)

    # SSH is picky about permissions
    try:
        KEYS_DIR.chmod(0o700)
    except Exception:
        logger.warning("ssh keys directory access right set is not successfull")

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
def get_admin_user_list() -> list():
    addon_options=load_json(ADDON_CONFIG_FILE, {})
    user_list = list()
    try:
        admin_users = addon_options["admin_users"]
        for admin in admin_users:
            user_list.append(admin["username"])
        if not admin_users:
            logger.warning("No Admin users identified from config file")
    except:
        logger.warning("No Admin users identified from config file")
    logger.info(f"Admin users list: {user_list}")
    return user_list


# -------------------------------------------------------------------
# Addon config helpers
# -------------------------------------------------------------------
def create_backup() -> Path:
    """
    Zips the configuration, keys, pending uploads, and history.
    Returns the path to the created zip file.
    """
    with zipfile.ZipFile(BACKUP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # List of items to include
        items_to_backup = [
            (KEYS_DIR, 'ssh_keys'),
            (PENDING_DIR, 'pending_uploads'),
            (SERVERS_FILE, 'servers.json'),
            (HISTORY_DIR, 'history'),
        ]

        for path, arcname in items_to_backup:
            if path.exists():
                if path.is_file():
                    zipf.write(path, arcname)
                else:
                    # Recursively add directory contents
                    for file in path.rglob('*'):
                        # arcname / relative path within the directory
                        zipf.write(file, arcname / file.relative_to(path))
    
    logger.info(f"Backup created at {BACKUP_FILE}")
    return BACKUP_FILE
