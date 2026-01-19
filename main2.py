#main2.py
import json
import os
import mimetypes
import nicegui
from nicegui import ui
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

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

# --- ADATKEZELÉS ---
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'
default_data = {"dropdown": "A", "text": "", "list_items": []}
state = default_data.copy()

def load_data():
    if os.path.exists(DATA_FILE):
        try: return json.load(open(DATA_FILE))
        except: return default_data.copy()
    return default_data.copy()

state = load_data()
list_textarea = None

def save_data():
    if list_textarea:
        state["list_items"] = [l.strip() for l in list_textarea.value.splitlines() if l.strip()]
        state["text"] = state.get("text", "")
        state["dropdown"] = state.get("dropdown", "")
        with open(DATA_FILE, 'w') as f: json.dump(state, f, indent=2)
        ui.notify('Mentve')

# --- UI ---
@ui.page('/')
def main_page():
    global list_textarea
    ui.dark_mode().enable()
    
    with ui.card().classes('w-full max-w-lg mx-auto p-4'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4')
        ui.select(["A", "B"], value=state["dropdown"]).bind_value(state, 'dropdown').classes('w-full')
        ui.input(placeholder='Szöveg').bind_value(state, 'text').classes('w-full')
        # Debounce a nagy listákhoz
        list_textarea = ui.textarea(value='\n'.join(state["list_items"])).classes('w-full').props('debounce=1000')
        ui.button('Mentés', on_click=save_data).classes('w-full mt-4')

ui.run_with(app, storage_secret='secret')

if __name__ == '__main__':
    import uvicorn
    # Port: 5005
    uvicorn.run("main:app", host="0.0.0.0", port=5002, reload=False, ws_max_size=10*1024*1024)
