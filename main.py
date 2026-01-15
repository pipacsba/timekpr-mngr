import os
import json
from nicegui import ui, app

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

def save_data():
    data_to_save = {
        "dropdown": state["dropdown"],
        "text": state["text"],
        "list_items": [line.strip() for line in list_textarea.value.splitlines() if line.strip()]
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    ui.notify('Sikeres mentés!', type='positive')

state = load_data()



@ui.page('/')
def main_page():
    ui.dark_mode().enable()
    
    with ui.card().classes('w-full max-w-lg mx-auto p-6'):
        ui.label('Beállítások').classes('text-2xl font-bold mb-4')

        ui.select(
            ["Opció A", "Opció B", "Opció C"],
            value=state["dropdown"]
        ).bind_value(state, 'dropdown').classes('w-full mb-4')

        ui.input('Egyedi elnevezés').bind_value(state, 'text').classes('w-full mb-4')

        global list_textarea
        list_textarea = ui.textarea(
            value='\n'.join(state["list_items"]),
            placeholder='Első elem\nMásodik elem'
        ).classes('w-full mb-6')

        ui.button('Mentés', on_click=save_data).classes('w-full bg-blue-600')

ui.run(
    host='0.0.0.0',
    port=5002,
    reload=False,
    show=False,   # important for HA
)
