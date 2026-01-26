# main.py
import os
import json
import mimetypes
import nicegui
from nicegui import ui
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import ui.navigation as navigation
from ssh_sync import run_sync_loop_with_stop

import logging
import sys
import threading #for ssh
from contextlib import asynccontextmanager # for ssh


# -------------------
# Logging setup
# -------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# -------------------
# MIME types (for HA Ingress static files)
# -------------------
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")


# =========================================================
# SSH BACKGROUND WORKER STATE
# =========================================================
stop_event = threading.Event()
ssh_thread: threading.Thread | None = None

# =========================================================
# FastAPI lifespan (MODERN + SAFE)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ssh_thread

    logger.info("Starting SSH sync worker")
    ssh_thread = threading.Thread(
        target=run_sync_loop_with_stop,
        args=(stop_event,),
        daemon=True,
        name="SSH-Sync",
    )
    ssh_thread.start()

    yield  # ---- application runs here ----

    logger.info("Stopping SSH sync worker")
    stop_event.set()


# -------------------
# FastAPI app (single ASGI root)
# -------------------
app = FastAPI(lifespan=lifespan)

# -------------------
# Ingress middleware (HTTP only)
# -------------------
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            request.scope["root_path"] = ingress_path
        return await call_next(request)

app.add_middleware(IngressMiddleware)

# -------------------
# Manual static serving for NiceGUI assets
# -------------------
nicegui_path = os.path.dirname(nicegui.__file__)
static_dir = os.path.join(nicegui_path, "static")
version = nicegui.__version__

@app.get(f"/_nicegui/{version}/static/{{file_path:path}}")
async def nicegui_static(file_path: str):
    full_path = os.path.join(static_dir, file_path)
    if not os.path.exists(full_path):
        return Response("Not found", status_code=404)

    media_type, _ = mimetypes.guess_type(full_path)
    media_type = media_type or "application/octet-stream"

    with open(full_path, "rb") as f:
        return Response(f.read(), media_type=media_type)

# -------------------
# Attach NiceGUI to FastAPI
# -------------------
ui.run_with(app, storage_secret="timekpr-secret")

# -------------------
# Uvicorn entrypoint
# -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200 * 1024 * 1024,
    )
