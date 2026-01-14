import json
import os
from nicegui import ui

# --- Adatkezelés ---
# Home Assistant add-onoknál a /data mappa az állandó tárhely
DATA_FILE = '/data/my_data.json' if os.path.exists('/data') else 'my_data.json'

# Alapértelmezett értékek
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

def save_data():
    # A textarea tartalmát listává alakítjuk mentés előtt
    data_to_save = {
        "dropdown": state["dropdown"],
        "text": state["text"],
        "list_items": [line.strip() for line in list_textarea.value.splitlines() if line.strip()]
    }
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    
    ui.notify('Sikeres mentés!', type='positive')

# Betöltjük az állapotot
state = load_data()

# --- Megjelenítés (UI) ---
@ui.page('/')
def main_page():
    # Sötét mód legyen alapértelmezett (jobban illik a HA-hoz)
    ui.dark_mode().enable()

    with ui.card().classes('w-full max-w-lg mx-auto p-6 q-pa-md items-stretch'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4 text-center')

        # 1. Dropdown
        ui.label('Válassz módot:')
        ui.select(["Opció A", "Opció B", "Opció C"], value=state["dropdown"]) \
            .bind_value(state, 'dropdown').classes('w-full mb-4')

        # 2. Szabad szöveg
        ui.label('Egyedi elnevezés:')
        ui.input(placeholder='Írj ide valamit...').bind_value(state, 'text').classes('w-full mb-4')

        # 3. Szabad szöveges lista
        # Itt egy trükköt használunk: Textarea-t mutatunk, de listaként kezeljük a háttérben
        ui.label('Lista elemek (soronként):')
        global list_textarea
        list_textarea = ui.textarea(
            value='\n'.join(state["list_items"]), 
            placeholder='Első elem\nMásodik elem'
        ).classes('w-full mb-6')

        # Gomb
        ui.button('Mentés', on_click=save_data).classes('w-full bg-blue-600')

        # Debug rész (hogy lásd, mit lát a Python a háttérben)
        with ui.expansion('Mentett adatok ellenőrzése', icon='bug_report').classes('mt-4 w-full'):
             ui.label().bind_text_from(state, 'dropdown', backward=lambda x: f"Mód: {x}")
             ui.label().bind_text_from(state, 'text', backward=lambda x: f"Szöveg: {x}")

# HA add-onban a host 0.0.0.0 kell legyen, a portot pedig a configban nyitjuk meg
ui.run(host='0.0.0.0', port=8080, title='HA Addon', reload=False)
