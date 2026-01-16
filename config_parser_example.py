from nicegui import ui
from pathlib import Path
import re

CONFIG_FILE = 'config.txt'


def parse_config(path: str):
    """
    Parse the configuration file into structured sections.
    """
    sections = []
    current_section = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.rstrip()

            if not raw:
                continue

            # Section header
            if raw.startswith('[') and raw.endswith(']'):
                current_section = {
                    'title': raw[1:-1],
                    'items': []
                }
                sections.append(current_section)
                continue

            # Comment line
            if raw.startswith('#'):
                if current_section is not None:
                    current_section['items'].append({
                        'type': 'comment',
                        'text': raw.lstrip('#').strip()
                    })
                continue

            # KEY = VALUE
            match = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', raw)
            if match and current_section is not None:
                key, value = match.groups()
                current_section['items'].append({
                    'type': 'field',
                    'key': key,
                    'value': value.strip()
                })

    return sections


def create_input(key, value):
    """
    Create appropriate input widget based on value type.
    """
    # Boolean
    if value in ('True', 'False'):
        return ui.switch(key, value=value == 'True')

    # Integer
    if value.isdigit():
        return ui.number(key, value=int(value))

    # Everything else -> text input
    return ui.input(key, value=value)


def build_ui(sections):
    ui.label('Configuration Editor').classes('text-2xl font-bold mb-4')

    for section in sections:
        with ui.card().classes('w-full mb-6'):
            ui.label(section['title']).classes('text-xl font-semibold mb-2')

            for item in section['items']:
                if item['type'] == 'comment':
                    ui.label(item['text']).classes(
                        'text-sm text-gray-600 italic'
                    )

                elif item['type'] == 'field':
                    create_input(item['key'], item['value']).classes(
                        'w-full'
                    )


@ui.page('/')
def index():
    sections = parse_config(CONFIG_FILE)
    build_ui(sections)


ui.run(title='Config Viewer')
