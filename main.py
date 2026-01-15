from fastapi import FastAPI
from nicegui import ui, app as nicegui_app


# ---------- ASGI wrapper for HA ingress ----------
class HassIngressASGIWrapper:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Handle both HTTP and WebSocket traffic
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")

            if path.startswith("/api/hassio_ingress/"):
                # Strip: /api/hassio_ingress/<TOKEN>
                parts = path.split("/", 3)
                new_path = "/" + (parts[3] if len(parts) > 3 else "")

                scope["path"] = new_path
                scope["raw_path"] = new_path.encode("utf-8")

        await self.app(scope, receive, send)


# ---------- FastAPI app ----------
fastapi_app = FastAPI()


# ---------- NiceGUI UI ----------
@ui.page("/")
def main_page():
    ui.dark_mode().enable()
    ui.label("NiceGUI behind Home Assistant ingress").classes("text-h5")
    ui.button("Test", on_click=lambda: ui.notify("Ingress OK 🎉"))


# ---------- Wrap and mount NiceGUI ----------
wrapped_nicegui_app = HassIngressASGIWrapper(nicegui_app)

fastapi_app.mount("/", wrapped_nicegui_app)


# ---------- Run with ----------
# uvicorn main:fastapi_app --host 0.0.0.0 --port 5002
