# main.py
"""
TimeKPR Next
- Slot-safe NiceGUI
- Background SSH sync
- Uvicorn deployment
"""

import json
import os
import mimetypes
import nicegui
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import threading
from nicegui import app as nicegui_app
from ui.navigation import register_routes
from ssh_sync import run_sync_loop


# 1. Kényszerítjük a MIME típusokat (Fonts hozzáadva!)
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")

app = FastAPI()

# Útvonalak előkészítése
nicegui_path = os.path.dirname(nicegui.__file__)
static_dir = os.path.join(nicegui_path, 'static')
version = nicegui.__version__

# --- A JAVÍTOTT KÉZI KISZOLGÁLÓ ---
# A változás: {file_path:path}
# Ez azt mondja a FastAPI-nak, hogy a perjeleket (/) is fogadja el,
# tehát a "fonts/file.woff2" is átjön, nem csak a "file.css".
@app.get(f"/_nicegui/{version}/static/{{file_path:path}}")
async def manual_static_serve(file_path: str):
    # Összerakjuk a teljes útvonalat
    full_path = os.path.join(static_dir, file_path)
    
    if os.path.exists(full_path):
        # Típus kitalálása
        media_type, _ = mimetypes.guess_type(full_path)
        if not media_type:
            # Fallback típusok, ha a guess nem megy
            if file_path.endswith('.woff2'): media_type = 'font/woff2'
            elif file_path.endswith('.css'): media_type = 'text/css'
            elif file_path.endswith('.js'): media_type = 'application/javascript'
            else: media_type = 'application/octet-stream'
            
        with open(full_path, 'rb') as f:
            content = f.read()
        return Response(content=content, media_type=media_type)
    
    return Response("File not found", status_code=404)

# --- INGRESS MIDDLEWARE ---
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            request.scope['root_path'] = ingress_path
        return await call_next(request)

app.add_middleware(IngressMiddleware)

# -------------------------------------------------------------------
# Initialize UI
# -------------------------------------------------------------------
# Routes are registered; headers/menus are created inside page callbacks
register_routes()


# -------------------------------------------------------------------
# Start background SSH sync in a daemon thread
# -------------------------------------------------------------------
threading.Thread(
    target=run_sync_loop,
    kwargs={'interval_seconds': 180},  # every 3 minutes
    daemon=True
).start()


# -------------------------------------------------------------------
# Expose ASGI app for Uvicorn
# -------------------------------------------------------------------
app = nicegui_app

ui.run_with(app, storage_secret='secret')

# -------------------------------------------------------------------
# Optional: run with Python directly (development)
# -------------------------------------------------------------------
if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024
    )
