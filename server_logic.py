# app.py
from nicegui import ui
from pathlib import Path
import json
import re
import time
import threading
import socket
import paramiko

import logging 
logger = logging.getLogger(__name__)
logger.info(f"server_logic.py is called at all")

# ============================================================
# Paths & constants
# ============================================================

DATA_ROOT = Path('/data')
SERVERS_FILE = DATA_ROOT / 'servers.json'
CACHE_DIR = DATA_ROOT / 'cache'
KEY_DIR = DATA_ROOT / 'ssh_keys'
PENDING_DIR = DATA_ROOT / 'pending_uploads'

SYNC_INTERVAL = 180  # 3 minutes

CONFIG_TYPES = {
    'server': 'Server Config',
    'user': 'User Config',
    'stats': 'User Statistics',
}

DEFAULT_REMOTE_PATHS = {
    'server': '/etc/timekpr/server.conf',
    'user': '/etc/timekpr/user.conf',
    'stats': '/var/lib/timekpr/stats.conf',
}

for p in (CACHE_DIR, KEY_DIR, PENDING_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ============================================================
# Utilities
# ============================================================

def load_servers():
    if not SERVERS_FILE.exists():
        return {}
    return json.loads(SERVERS_FILE.read_text())


def save_servers(servers):
    SERVERS_FILE.write_text(json.dumps(servers, indent=2))


def server_up(host, port=22, timeout=5):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


# ============================================================
# Config parsing / serialization (Program1 logic)
# ============================================================

def parse_config(path: Path):
    data = []
    current = None

    for line in path.read_text().splitlines():
        if line.startswith('[') and line.endswith(']'):
            current = {'title': line[1:-1], 'items': []}
            data.append(current)
            continue

        if line.startswith('#'):
            if current:
                current['items'].append({'type': 'comment', 'text': line})
            continue

        m = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', line)
        if m and current:
            key, value = m.groups()
            current['items'].append({
                'type': 'field',
                'key': key,
                'value': value,
            })

    return data


def write_config(data, path: Path):
    lines = []
    for section in data:
        lines.append(f'[{section["title"]}]')
        for item in section['items']:
            if item['type'] == 'comment':
                lines.append(item['text'])
            else:
                lines.append(f'{item["key"]} = {item["value"]}')
        lines.append('')
    path.write_text('\n'.join(lines))


# ============================================================
# Background sync (Program2 logic)
# ============================================================

def sync_loop():
    while True:
        servers = load_servers()

        for name, cfg in servers.items():
            if not server_up(cfg['host'], cfg.get('port', 22)):
                continue

            cache = CACHE_DIR / name
            cache.mkdir(exist_ok=True)

            key_path = KEY_DIR / cfg['key']

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                cfg['host'],
                username=cfg['user'],
                key_filename=str(key_path),
                port=cfg.get('port', 22),
            )

            sftp = ssh.open_sftp()

            # download
            for kind, remote in cfg['paths'].items():
                local = cache / f'{kind}.conf'
                sftp.get(remote, str(local))

            # upload pending
            pending = PENDING_DIR / name
            if pending.exists():
                for f in pending.iterdir():
                    sftp.put(str(f), cfg['paths'][f.stem])
                for f in pending.iterdir():
                    f.unlink()
                pending.rmdir()

            sftp.close()
            ssh.close()

        time.sleep(SYNC_INTERVAL)


threading.Thread(target=sync_loop, daemon=True).start()

# ============================================================
# UI state
# ============================================================

current_server = {'name': None}

# ============================================================
# UI helpers
# ============================================================

def navigation():
    with ui.row().classes('gap-4 mb-4'):
        ui.link('Dashboard', '/')
        ui.link('Servers', '/servers')
        if current_server['name']:
            for k in CONFIG_TYPES:
                ui.link(CONFIG_TYPES[k], f'/config/{k}')


def no_server_page():
    ui.label('No server found').classes('text-2xl text-red-600')
    ui.label('Configure a remote server first.')


def render_editor(kind):
    server = current_server['name']
    servers = load_servers()

    if not server or server not in servers:
        no_server_page()
        return

    file = CACHE_DIR / server / f'{kind}.conf'
    if not file.exists():
        no_server_page()
        return

    data = parse_config(file)

    for section in data:
        with ui.card().classes('mb-4 w-full'):
            ui.label(section['title']).classes('text-xl font-semibold')

            for item in section['items']:
                if item['type'] == 'comment':
                    ui.label(item['text'].lstrip('#')).classes(
                        'text-sm text-gray-600 italic'
                    )
                else:
                    val = item['value']
                    if val in ('True', 'False'):
                        ui.switch(
                            item['key'],
                            value=val == 'True',
                            on_change=lambda e, i=item: i.update(
                                value=str(e.value)
                            ),
                        )
                    elif val.isdigit():
                        ui.number(
                            item['key'],
                            value=int(val),
                            on_change=lambda e, i=item: i.update(
                                value=str(int(e.value))
                            ),
                        )
                    else:
                        ui.input(
                            item['key'],
                            value=val,
                            on_change=lambda e, i=item: i.update(
                                value=e.value
                            ),
                        )

    def save():
        write_config(data, file)

        cfg = s
