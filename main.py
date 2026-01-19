"""
TimeKPR Manager
- Slot-safe NiceGUI
- Background SSH sync
- HA ingress / Uvicorn ready
"""

import os
import json
import mimetypes
import threading
from pathlib import Path

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import ui, app as nicegui_app

from ui.navigation import register_routes
from ssh_sync import run_sync_loop

# -------------------------------------------------------------------
# Force MIME types for fonts and JS/CSS
# -------------------------------------------------------------------
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")

# -------------------------------------------------------------------
# FastAPI root app
# -------------------------------------------------------------------
app = FastAPI()

# -------------------------------------------------------------------
# Manual static server (needed for HA ingress / nicegui static)
# -------------------------------------------------------------------
nicegui_path = Path(__import__('nicegui').__file__).parent
static_dir = nicegui_path / 'static'
version = __import__('nicegui').__version__

@app.get(f"/_nicegui/{version}/static/{{file_path:path}}")
async def manual_static_serve(file_path: str):
    full_path = static_dir / file_path
    if not full_path.exists():
        return Response("File not found", status_code=404)

    media_type, _ = mimetypes.guess_type(str(full_path))
    if not media_type:
        if file_path.endswith('.woff2'):
            media_type = 'font/woff2'
        elif file_path.endswith('.woff'):
            media_type = 'font/woff'
        elif file_path.endswith('.css'):
            media_type = 'text/css'
        elif file_path.endswith('.js'):
            media_type = 'application/javascript'
        else:
            media_type = 'application/octet-stream'

    return Response(content=full_path.read_bytes(), media_type=media_type)

# -------------------------------------------------------------------
# Ingress middleware
# -------------------------------------------------------------------
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            request.scope['root_path'] = ingress_path
        return await call_next(request)

app.add_middleware(IngressMiddleware)

# -------------------------------------------------------------------
# Persistent storage path
# -------------------------------------------------------------------
DATA_DIR = Path('/data') if Path('/data').exists() else Path('.')
DATA_FILE = DATA_DIR / 'my_data.json'

# Ensure storage exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load state
default_state = {"dropdown": "A", "text": "", "list_items": []}

def load_state():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except json.JSONDecodeError:
            return default_state.copy()
    return default_state.copy()

state = load_state()
list_textarea = None

def save_state():
    if list_textarea:
        state["list_items"] = [l.strip() for l in list_textarea.value.splitlines() if l.strip()]
        with open(DATA_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        ui.notify('Saved')

# -------------------------------------------------------------------
# Register NiceGUI pages / routes
# -------------------------------------------------------------------
register_routes()

# -------------------------------------------------------------------
# Background SSH sync thread
# -------------------------------------------------------------------
threading.Thread(
    target=run_sync_loop,
    kwargs={'interval_seconds': 180},  # every 3 minutes
    daemon=True
).start()

# -------------------------------------------------------------------
# Expose ASGI app for Uvicorn
# -------------------------------------------------------------------
app = nicegui_app  # <- important: exposes NiceGUI as FastAPI app

# -------------------------------------------------------------------
# Optional direct run for development
# -------------------------------------------------------------------
if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024,
    )
