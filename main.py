from nicegui import ui
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope["path"]
        if path.startswith("/api/hassio_ingress/"):
            parts = path.split("/", 3)
            request.scope["path"] = "/" + (parts[3] if len(parts) > 3 else "")
        return await call_next(request)

@ui.page('/')
def main():
    ui.label('Hello from NiceGUI behind HA ingress')

# IMPORTANT: do NOT call ui.run()
app = ui.app
app.add_middleware(IngressMiddleware)
