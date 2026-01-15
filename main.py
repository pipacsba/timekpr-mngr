from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import ui

# ---------- Middleware ----------
class HassIngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope['path']

        if path.startswith('/api/hassio_ingress/'):
            # strip: /api/hassio_ingress/<TOKEN>
            parts = path.split('/', 3)
            request.scope['path'] = '/' + (parts[3] if len(parts) > 3 else '')

        return await call_next(request)


# ---------- FastAPI app ----------
fastapi_app = FastAPI()
fastapi_app.add_middleware(HassIngressMiddleware)


# ---------- NiceGUI UI ----------
@ui.page('/')
def main_page():
    ui.dark_mode().enable()
    ui.label('NiceGUI behind Home Assistant ingress').classes('text-h5')
    ui.button('Works 🎉', on_click=lambda: ui.notify('Ingress OK'))


# ---------- Mount NiceGUI ----------
# IMPORTANT: mount ui.app, not ui.run()
fastapi_app.mount('/', ui.app)


# ---------- Entry point ----------
# Run with: uvicorn main:fastapi_app --host 0.0.0.0 --port 5002
