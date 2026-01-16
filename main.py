import json
import os
import mimetypes
import nicegui # <-- EZ HIÁNYZOTT AZ ELŐBB
from nicegui import ui
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

# 1. VÉDELEM: Kényszerítjük a típusokat (Alpine Linux miatt)
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

app = FastAPI()

# 2. VÉDELEM: Kézi statikus fájl kiszolgálás
# Megkeressük, hol van telepítve a nicegui csomag a konténerben
try:
    nicegui_path = os.path.dirname(nicegui.__file__)
    static_dir = os.path.join(nicegui_path, 'static')
    version = nicegui.__version__
    
    print(f"DEBUG: NiceGUI path: {nicegui_path}")
    print(f"DEBUG: Static dir: {static_dir}")

    if os.path.exists(static_dir):
        # A FastAPI-nak megmondjuk: "Ha bárki a /_nicegui/VERZIO/static-ot keresi,
        # szolgáld ki direktben ebből a mappából."
        app.mount(
            f'/_nicegui/{version}/static', 
            StaticFiles(directory=static_dir), 
            name='force_static'
        )
        print("DEBUG: Statikus fájlok kézi mountolása SIKERES.")
    else:
        print("DEBUG: HIBA - A static mappa nem található!")
except Exception as e:
    print(f"DEBUG: Hiba a mountolás közben: {e}")

# 3. VÉDELEM: Ingress Middleware (Hogy a HA proxy működjön)
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            request.scope['root_path'] = ingress_path
        return await call_next(request)

app.add_middleware(IngressMiddleware)

# --- ADATKEZELÉS ---
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'
default_data = {"dropdown": "Opció A", "text": "", "list_items": []}

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
    # Sötét mód (most már be kell töltenie a CSS-t hozzá)
    ui.dark_mode().enable()
    
    with ui.card().classes('w-full max-w-lg mx-auto p-4'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4')
        
        ui.select(["A", "B", "C"], value=state["dropdown"]).bind_value(state, 'dropdown').classes('w-full')
        
        ui.input(placeholder='Szöveg').bind_value(state, 'text').classes('w-full')
        
        list_textarea = ui.textarea(value='\n'.join(state["list_items"])).classes('w-full').props('debounce=1000')
        
        ui.button('Mentés', on_click=save_data).classes('w-full mt-4')

# Indítás
ui.run_with(app, storage_secret='secret_key_random')

if __name__ == '__main__':
    import uvicorn
    # 5005-ös port (Alpine + Config szerint)
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=5002, 
        reload=False, 
        ws_max_size=200*1024*1024
    )
