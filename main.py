import json
import os
from nicegui import ui, app # Importáljuk az 'app'-ot is
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# --- INGRESS FIX START ---
# Ez a middleware figyeli a HA által küldött fejlécet és beállítja az útvonalat
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # A Home Assistant ebben a fejlécben küldi a dinamikus útvonalat
        ingress_path = request.headers.get("X-Ingress-Path")
        
        if ingress_path:
            # Beállítjuk a root_path-t, így a NiceGUI tudni fogja,
            # hogy pl. a /_nicegui/ws helyett a /api/hassio_ingress/xyz/_nicegui/ws-re kell csatlakozni
            request.scope['root_path'] = ingress_path
            
        response = await call_next(request)
        return response

# Hozzáadjuk a middleware-t az alkalmazáshoz
app.add_middleware(IngressMiddleware)
# --- INGRESS FIX END ---

# --- Adatkezelés (változatlan) ---
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'

default_data = {
    "dropdown": "Opció A",
    "text": "",
    "list_items": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_data.copy()

state = load_data()

def save_data():
    data_to_save = {
        "dropdown": state["dropdown"],
        "text": state["text"],
        "list_items": [line.strip() for line in list_textarea.value.splitlines() if line.strip()]
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    ui.notify('Sikeres mentés!', type='positive')

# --- Megjelenítés (Kicsit csinosítva) ---
@ui.page('/')
def main_page():
    ui.dark_mode().enable()

    with ui.card().classes('w-full max-w-lg mx-auto p-6 q-pa-md items-stretch'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4 text-center')

        ui.label('Válassz módot:')
        ui.select(["Opció A", "Opció B", "Opció C"], value=state["dropdown"]) \
            .bind_value(state, 'dropdown').classes('w-full mb-4')

        ui.label('Egyedi elnevezés:')
        ui.input(placeholder='Írj ide valamit...').bind_value(state, 'text').classes('w-full mb-4')

        ui.label('Lista elemek (soronként):')
        global list_textarea
        list_textarea = ui.textarea(
            value='\n'.join(state["list_items"]), 
            placeholder='Első elem\nMásodik elem'
        ).classes('w-full mb-6')

        ui.button('Mentés', on_click=save_data).classes('w-full bg-blue-600')

# Fontos: Ingress használatakor a portot nem a böngészőben nyitod meg,
# de a belső webszervernek futnia kell valahol (pl. 8080).
ui.run(host='0.0.0.0', port=5002, title='HA Addon', reload=False)
