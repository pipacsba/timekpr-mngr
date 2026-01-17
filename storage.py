from pathlib import Path
import json

DATA_ROOT = Path('/Data')
CACHE = DATA_ROOT / 'cache'
KEYS = DATA_ROOT / 'ssh_keys'
PENDING = DATA_ROOT / 'pending_uploads'
SERVERS_FILE = DATA_ROOT / 'servers.json'

for p in (CACHE, KEYS, PENDING):
    p.mkdir(parents=True, exist_ok=True)

def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))
