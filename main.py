import json
import os
import mimetypes
import nicegui
from nicegui import ui
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# 1. Kényszerítjük a MIME típusokat (Alpine miatt továbbra is kell)
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

app = FastAPI()

# Útvonalak előkészítése a kézi kiszolgáláshoz
nicegui_path = os.path.dirname(nicegui.__file__)
static_dir = os.path.join(nicegui_path, 'static')
version = nicegui.__version__

# --- A MEGOLDÁS: KÉZI FILE KISZOLGÁLÁS ---
# Mivel a `mount` nem működik, létrehozunk egy konkrét végpontot,
# ami elkapja a static fájlokra érkező kéréseket, és byte-ról byte-ra visszaadja őket.
@app.get(f"/_nicegui/{version}/static/{{filename}}")
async def manual_static_serve(filename: str):
    file_path = os.path.join(static_dir, filename)
    
    if os.path.exists(file_path):
        # Kitaláljuk a fájl típusát
        media_type, _ = mimetypes.guess_type(file_path)
        if not media_type:
            # Ha nem sikerült kitalálni, kézzel segítünk
            if filename.endswith('.css'): media_type = 'text/css'
            elif filename.endswith('.js'): media_type = 'application/javascript'
            else: media_type = 'application/octet-stream'
            
        # Felolvassuk és visszaküldjük
        with open(file_path, 'rb') as f:
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

# UI Indítása a saját appunkon
ui.run_with(app, storage_secret='secret_key')

if __name__ == '__main__':
    import uvicorn
    # A te portod: 5005
    uvicorn.run("main:app", host="0.0.0.0", port=5002, reload=False, ws_max_size=200*1024*1024)
