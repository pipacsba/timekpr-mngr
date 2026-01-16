import json
import os
from nicegui import ui
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

# 1. LÉPÉS: Saját FastAPI app létrehozása
# Így teljes kontrollunk van a szerver felett, még mielőtt a NiceGUI elindulna
app = FastAPI()

# 2. LÉPÉS: Az Ingress Middleware (A javítás)
class IngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Megnézzük, hogy a Home Assistant küldött-e Ingress fejlécet
        ingress_path = request.headers.get("X-Ingress-Path")
        
        if ingress_path:
            # Ha van ingress path (pl. /api/hassio_ingress/TOKEN),
            # akkor beállítjuk ezt root_path-nak.
            # Így a NiceGUI tudni fogja, hogy minden linket ezzel kell kezdeni.
            request.scope['root_path'] = ingress_path
        
        # Opcionális debug: Ha látni akarod a logban, mi történik
        # print(f"Path: {request.url.path}, Root: {request.scope.get('root_path')}")
        
        return await call_next(request)

# Hozzáadjuk a middleware-t a saját appunkhoz
app.add_middleware(IngressMiddleware)

# --- ADATKEZELÉS (Változatlan) ---
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'

default_data = {
    "dropdown": "Opció A",
    "text": "",
    "list_items": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default_data.copy()
    return default_data.copy()

state = load_data()

# Fontos: A textarea változót itt deklaráljuk, hogy elérhető legyen a save_data-ban
list_textarea = None

def save_data():
    if list_textarea is None: return
    
    data_to_save = {
        "dropdown": state["dropdown"],
        "text": state["text"],
        "list_items": [line.strip() for line in list_textarea.value.splitlines() if line.strip()]
    }
    
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        ui.notify('Sikeres mentés!', type='positive')
    except Exception as e:
        ui.notify(f'Hiba a mentéskor: {e}', type='negative')

# --- MEGJELENÍTÉS (UI) ---
@ui.page('/')
def main_page():
    global list_textarea
    ui.dark_mode().enable()

    with ui.card().classes('w-full max-w-lg mx-auto p-6 q-pa-md items-stretch'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4 text-center')

        ui.label('Válassz módot:')
        ui.select(["Opció A", "Opció B", "Opció C"], value=state["dropdown"]) \
            .bind_value(state, 'dropdown').classes('w-full mb-4')

        ui.label('Egyedi elnevezés:')
        ui.input(placeholder='Írj ide valamit...').bind_value(state, 'text').classes('w-full mb-4')

        ui.label('Lista elemek (soronként):')
        list_textarea = ui.textarea(
            value='\n'.join(state["list_items"]), 
            placeholder='Első elem\nMásodik elem'
        ).classes('w-full mb-6')

        ui.button('Mentés', on_click=save_data).classes('w-full bg-blue-600')
        
        # Debug infó
        with ui.expansion('Debug Infó').classes('mt-4'):
             ui.label('Ha ezt látod, a JS és CSS betöltött!').classes('text-green-500')

# 3. LÉPÉS: Indítás a ui.run_with segítségével
# Ez a kulcs: Nem a ui.run()-t hívjuk, hanem rákötjük a NiceGUI-t a már beállított szerverünkre.
# A storage_secret fontos a session kezeléshez
ui.run_with(
    app, 
    title='HA Addon',
    storage_secret='random_string_ide',
)

# Megjegyzés: Ha ui.run_with-et használsz, a uvicorn indítást dockerben
# a main.py alján lévő "if __name__..." helyett máshogy is lehet kezelni,
# de egyszerűbb, ha hagyjuk, hogy a Dockerfile CMD parancsa indítsa a uvicorn-t.
#
# A fejlesztéshez/futtatáshoz viszont kell ez a blokk, ha "python main.py"-t futtatsz:
if __name__ == '__main__':
    import uvicorn
    # A config.yaml-ben megadott port (8080)
    uvicorn.run("main:app", host="0.0.0.0", port=5002, reload=False)
