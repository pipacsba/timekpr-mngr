# main.py
"""
TimeKPR Manager – slot-safe, HA Ingress / Uvicorn compatible

- /data storage
- Slot-safe UI with first-run welcome page
- Background SSH sync
"""

import os
import mimetypes
import threading
from pathlib import Path

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import nicegui
from nicegui import ui
from nicegui import app as nicegui_app

from ui.navigation import register_routes
from ssh_sync import run_sync_loop
from storage import DATA_ROOT, KEYS_DIR, _ensure_dirs

import logging
import sys

# -------------------------------------------------------------------
# Global logging setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,              # DEBUG for more detail
    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Something works... at least I can log!")


# -------------------------------------------------------------------
# 1. Ensure directories exist
# -------------------------------------------------------------------
_ensure_dirs()
KEYS_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# 2. Force MIME types for fonts and JS/CSS
# -------------------------------------------------------------------
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")

# -------------------------------------------------------------------
# 3. FastAPI app
# -------------------------------------------------------------------
fastapi_app = FastAPI()

# Serve NiceGUI static manually
nicegui_path = os.path.dirname(nicegui.__file__)
static_dir = os.path.join(nicegui_path, "static")
version = nicegui.__version__

@fastapi_app.get(f"/_nicegui/{version}/static/{{file_path:path}}")
async def manual_static_serve(file_path: str):
    full_path = os.path.join(static_dir, file_path)
    if os.path.exists(full_path):
        media_type, _ = mimetypes.guess_type(full_path)
        if not media_type:
            if file_path.endswith('.woff2'): media_type = 'font/woff2'
            elif file_path.endswith('.css'): media_type = 'text/css'
            elif file_path.endswith('.js'): media_type = 'application/javascript'
            else: media_type = 'application/octet-stream'
        with open(full_path, 'rb') as f:
            return Response(f.read(), media_type=media_type)
    return Response("File not found", status_code=404)

# HA Ingress middleware
class IngressMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = dict(scope.get('headers', []))
            ingress_path = headers.get(b'x-ingress-path')
            if ingress_path:
                scope['root_path'] = ingress_path.decode()
        await self.app(scope, receive, send)

fastapi_app.add_middleware(BaseHTTPMiddleware, dispatch=IngressMiddleware(fastapi_app))

# -------------------------------------------------------------------
# 4. Initialize NiceGUI
# -------------------------------------------------------------------
# Attach to FastAPI app
nicegui_app = nicegui.app
nicegui_app.fastapi_app = fastapi_app

# Register all routes
register_routes()
logger.info(f"Register routes finished!")

# -------------------------------------------------------------------
# 5. Start background SSH sync (daemon thread)
# -------------------------------------------------------------------
threading.Thread(
    target=run_sync_loop,
    kwargs={'interval_seconds': 180},
    daemon=True,
).start()

# -------------------------------------------------------------------
# 6. Expose FastAPI app for Uvicorn
# -------------------------------------------------------------------
app = nicegui_app  # Uvicorn entrypoint
# This initializes NiceGUI internals for Uvicorn
ui.run_with(app, storage_secret='secret')

# -------------------------------------------------------------------
# 7. Optional: development run with Python directly
# -------------------------------------------------------------------
if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024,
        log_level="info",
        app_dir=str(Path(__file__).parent),
    )
