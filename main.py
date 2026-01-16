import json
import os
import mimetypes
import nicegui
from nicegui import ui
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import Response

# Kényszerítjük a MIME típusokat
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

app = FastAPI()

# --- DIAGNOSZTIKA START ---
print("\n" + "="*40)
print(" RÉSZLETES DIAGNOSZTIKA INDULÁSA")
print("="*40)

# 1. Verzió ellenőrzése
version = nicegui.__version__
print(f"DEBUG: Python NiceGUI Verzió: '{version}'")

# 2. Útvonalak ellenőrzése
nicegui_path = os.path.dirname(nicegui.__file__)
static_dir = os.path.join(nicegui_path, 'static')
print(f"DEBUG: Keresett mappa: {static_dir}")

# 3. Mappa tartalmának listázása (EZ A KULCS!)
if os.path.exists(static_dir):
    print(f"DEBUG: A mappa létezik. Tartalma:")
    try:
        files = os.listdir(static_dir)
        for f in files:
            print(f"  - {f}")
            
        if 'fonts.css' in files:
            print("DEBUG: EREDMÉNY -> A fonts.css OTT VAN!")
        else:
            print("DEBUG: EREDMÉNY -> A fonts.css HIÁNYZIK! (Ez a baj!)")
    except Exception as e:
        print(f"DEBUG: Hiba a listázáskor: {e}")
else:
    print("DEBUG: KRITIKUS HIBA -> A mappa nem létezik!")

# 4. Manuális Mount (dinamikus verzióval)
if os.path.exists(static_dir):
    mount_path = f'/_nicegui/{version}/static'
    print(f"DEBUG: Mountolás ide: {mount_path}")
    app.mount(mount_path, StaticFiles(directory=static_dir), name='force_static')

print("="*40 + "\n")
# --- DIAGNOSZTIKA END ---


# --- INGRESS MIDDLEWARE ---
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            request.scope['root_path'] = ingress_path
        return await call_next(request)

app.add_middleware(IngressMiddleware)

# --- DIRECT CSS TESZT ENDPOINT ---
# Ez egy B-terv: ha a staticfiles nem megy, ez direktben felolvassa a fájlt
@app.get("/debug_css")
def debug_css():
    file_path = os.path.join(static_dir, 'fonts.css')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/css")
    return Response(content="Fajl nem talalhato", status_code=404)


# --- ADATKEZELÉS ---
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'
default_data = {"dropdown": "A", "text": "", "list_items": []}
state = default_data.copy()
if os.path.exists(DATA_FILE):
    try: state = json.load(open(DATA_FILE))
    except: pass
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
        list_textarea = ui.textarea(value='\n'.join(state["list_items"])).classes('w-full').props('debounce=1000')
        ui.button('Mentés', on_click=save_data).classes('w-full mt-4')

ui.run_with(app, storage_secret='secret')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5005, reload=False, ws_max_size=200*1024*1024)
