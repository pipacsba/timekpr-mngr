from nicegui import ui
from pathlib import Path
import re

CONFIGS = {
    'server': {
        'title': 'Server Configuration',
        'file': 'configs/server.conf',
    },
    'user': {
        'title': 'User Configuration',
        'file': 'configs/user.conf',
    },
    'stats': {
        'title': 'User Statistics',
        'file': 'configs/user_stats.conf',
    },
}


# ---------- Parsing ----------

def parse_config(path: str):
    sections = []
    current = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.rstrip()
            if not raw:
                continue

            # [SECTION]
            if raw.startswith('[') and raw.endswith(']'):
                current = {
                    'title': raw[1:-1],
                    'items': []
                }
                sections.append(current)
                continue

            # Comments
            if raw.startswith('#'):
                if current:
                    current['items'].append({
                        'type': 'comment',
                        'text': raw.lstrip('#').strip()
                    })
                continue

            # KEY = VALUE
            m = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', raw)
            if m and current:
                key, value = m.groups()
                current['items'].append({
                    'type': 'field',
                    'key': key,
                    'value': value.strip()
                })

    return sections


# ---------- UI helpers ----------

def create_input(key, value):
    if value in ('True', 'False'):
        return ui.switch(key, value=value == 'True')

    if value.isdigit():
        return ui.number(key, value=int(value))

    return ui.input(key, value=value)


def render_config_page(title: str, filepath: str):
    ui.label(title).classes('text-2xl font-bold mb-4')

    sections = parse_config(filepath)

    for section in sections:
        with ui.card().classes('w-full mb-6'):
            ui.label(section['title']).classes('text-xl font-semibold mb-2')

            for item in section['items']:
                if item['type'] == 'comment':
                    ui.label(item['text']).classes(
                        'text-sm text-gray-600 italic'
                    )
                elif item['type'] == 'field':
                    create_input(item['key'], item['value']).classes('w-full')


def navigation():
    with ui.row().classes('mb-6 gap-4'):
        ui.link('Server Config', '/server')
        ui.link('User Config', '/user')
        ui.link('User Statistics', '/stats')


# ---------- Pages ----------

@ui.page('/')
def index():
    ui.label('TimeKPR Configuration').classes('text-3xl font-bold mb-4')
    navigation()
    ui.label('Select a configuration page above.')


@ui.page('/server')
def server_config():
    navigation()
    render_config_page(
        CONFIGS['server']['title'],
        CONFIGS['server']['file'],
    )


@ui.page('/user')
def user_config():
    navigation()
    render_config_page(
        CONFIGS['user']['title'],
        CONFIGS['user']['file'],
    )


@ui.page('/stats')
def stats_page():
    navigation()
    render_config_page(
        CONFIGS['stats']['title'],
        CONFIGS['stats']['file'],
    )


ui.run(title='TimeKPR Config Manager')
