from nicegui import ui
from pathlib import Path
import re

CONFIGS = {
    'server': ('Server Configuration', 'configs/server.conf'),
    'user': ('User Configuration', 'configs/user.conf'),
    'stats': ('User Statistics', 'configs/user_stats.conf'),
}


# ---------- Parsing ----------

def parse_config(path: str):
    data = []
    current_section = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.rstrip('\n')

            if raw.startswith('[') and raw.endswith(']'):
                current_section = {
                    'type': 'section',
                    'title': raw[1:-1],
                    'items': []
                }
                data.append(current_section)
                continue

            if raw.startswith('#'):
                if current_section:
                    current_section['items'].append({
                        'type': 'comment',
                        'text': raw
                    })
                continue

            m = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', raw)
            if m and current_section:
                key, value = m.groups()
                current_section['items'].append({
                    'type': 'field',
                    'key': key,
                    'value': value
                })

    return data


# ---------- Serialization ----------

def save_config(data, target_file: str):
    lines = []

    for section in data:
        lines.append(f'[{section["title"]}]')

        for item in section['items']:
            if item['type'] == 'comment':
                lines.append(item['text'])

            elif item['type'] == 'field':
                lines.append(f'{item["key"]} = {item["value"]}')

        lines.append('')  # blank line between sections

    Path(target_file).write_text('\n'.join(lines), encoding='utf-8')


# ---------- UI helpers ----------

def create_input(item):
    value = item['value']

    if value in ('True', 'False'):
        return ui.switch(
            item['key'],
            value=value == 'True',
            on_change=lambda e: item.update(
                value=str(e.value)
            ),
        )

    if value.isdigit():
        return ui.number(
            item['key'],
            value=int(value),
            on_change=lambda e: item.update(
                value=str(int(e.value))
            ),
        )

    return ui.input(
        item['key'],
        value=value,
        on_change=lambda e: item.update(
            value=e.value
        ),
    )


def render_page(title, filepath):
    ui.label(title).classes('text-2xl font-bold mb-4')

    config_data = parse_config(filepath)

    for section in config_data:
        with ui.card().classes('w-full mb-6'):
            ui.label(section['title']).classes('text-xl font-semibold mb-2')

            for item in section['items']:
                if item['type'] == 'comment':
                    ui.label(item['text'].lstrip('#').strip()).classes(
                        'text-sm text-gray-600 italic'
                    )

                elif item['type'] == 'field':
                    create_input(item).classes('w-full')

    # Save As
    with ui.row().classes('mt-6'):
        target = ui.input(
            'Save as file',
            placeholder='configs/new_config.conf',
        ).classes('w-96')

        ui.button(
            'Save',
            on_click=lambda: (
                save_config(config_data, target.value),
                ui.notify(f'Saved to {target.value}')
            )
        ).props('color=primary')


def navigation():
    with ui.row().classes('mb-6 gap-4'):
        ui.link('Server', '/server')
        ui.link('User', '/user')
        ui.link('Statistics', '/stats')


# ---------- Pages ----------

@ui.page('/')
def index():
    ui.label('TimeKPR Configuration Manager').classes(
        'text-3xl font-bold mb-4'
    )
    navigation()


@ui.page('/server')
def server():
    navigation()
    render_page(*CONFIGS['server'])


@ui.page('/user')
def user():
    navigation()
    render_page(*CONFIGS['user'])


@ui.page('/stats')
def stats():
    navigation()
    render_page(*CONFIGS['stats'])


ui.run(title='Config Manager')

