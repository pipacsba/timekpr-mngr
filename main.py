# main.py
"""
TimeKPR Manager – HA Ingress / Uvicorn compatible
- Slot-safe UI with first-run welcome page
- Background SSH sync safe
"""

import os
import mimetypes
import threading
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

import nicegui
from nicegui import ui

from ui.navigation import register_routes
from ssh_sync import run_sync_loop
from storage import DATA_ROOT, KEYS_DIR, _ensure_dirs

import logging
import sys

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
logger.info("Starting TimeKPR Manager...")

# -------------------------------------------------------------------
# Ensure directories exist
# -------------------------------------------------------------------
_ensure_dirs()
KEYS_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Force MIME types for fonts & JS/CSS
# -------------------------------------------------------------------
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
fastapi_app = FastAPI()

# -------------------------------------------------------------------
# HA Ingress middleware
# -------------------------------------------------------------------
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            # Apply HA Ingress root path
            request.scope["root_path"] = ingress_path
        return await call_next(request)

fastapi_app.add_middleware(IngressMiddleware)

# -------------------------------------------------------------------
# Attach NiceGUI to FastAPI
# -------------------------------------------------------------------
nicegui_app = nicegui.app
nicegui_app.fastapi_app = fastapi_app

# Register all UI routes
register_routes()
logger.info("UI routes registered.")

# -------------------------------------------------------------------
# Background SSH sync
# -------------------------------------------------------------------
threading.Thread(
    target=run_sync_loop,
    kwargs={"interval_seconds": 180},
    daemon=True,
).start()
logger.info("Background SSH sync started.")

# -------------------------------------------------------------------
# Expose app for Uvicorn
# -------------------------------------------------------------------
app = nicegui_app  # Uvicorn entrypoint

# -------------------------------------------------------------------
# Run NiceGUI
# -------------------------------------------------------------------
ui.run_with(app, storage_secret="secret")

# -------------------------------------------------------------------
# Optional: direct Python run
# -------------------------------------------------------------------
if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=20*1024*1024,
        log_level="info",
        app_dir=str(Path(__file__).parent),
    )
