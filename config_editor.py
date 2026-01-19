# app/config_editor.py
"""
Config parser + editor builder.

Understands:
- [SECTION] headers
- #### or # comments
- KEY = VALUE entries

Preserves formatting on save.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from nicegui import ui

from storage import (
    server_cache_dir,
    user_cache_dir,
    stats_cache_dir,
    pending_dir,
    pending_user_dir,
    pending_stats_dir,
)

import logging 
logger = logging.getLogger(__name__)
logger.info(f"config_editor.py is called at all")

# -------------------------------------------------------------------
# Data model
# -------------------------------------------------------------------

@dataclass
class Line:
    raw: str


@dataclass
class Header(Line):
    name: str


@dataclass
class Comment(Line):
    pass


@dataclass
class Entry(Line):
    key: str
    value: str


# -------------------------------------------------------------------
# Parser
# -------------------------------------------------------------------

def parse_config(text: str) -> List[Line]:
    lines: List[Line] = []

    for raw in text.splitlines():
        stripped = raw.strip()

        if stripped.startswith('[') and stripped.endswith(']'):
            lines.append(Header(raw=raw, name=stripped[1:-1]))

        elif stripped.startswith('#'):
            lines.append(Comment(raw=raw))

        elif '=' in raw:
            key, value = raw.split('=', 1)
            lines.append(Entry(
                raw=raw,
                key=key.strip(),
                value=value.strip()
            ))
        else:
            lines.append(Line(raw=raw))

    return lines


def serialize_config(lines: List[Line], values: Dict[str, str]) -> str:
    out: List[str] = []

    for line in lines:
        if isinstance(line, Entry):
            val = values.get(line.key, line.value)
            out.append(f'{line.key} = {val}')
        else:
            out.append(line.raw)

    return '\n'.join(out) + '\n'


# -------------------------------------------------------------------
# File loaders
# -------------------------------------------------------------------

def load_config(path: Path) -> Optional[List[Line]]:
    if not path.exists():
        return None
    return parse_config(path.read_text())


# -------------------------------------------------------------------
# NiceGUI editor
# -------------------------------------------------------------------

def render_editor(
    *,
    server_name: str,
    config_type: str,
    username: Optional[str] = None,
) -> None:
    """
    config_type: 'server' | 'user' | 'stats'
    """

    if config_type == 'server':
        file_path = server_cache_dir(server_name) / 'server.conf'
        pending_path = pending_dir(server_name) / 'server.conf'

    elif config_type == 'user':
        file_path = user_cache_dir(server_name) / f'{username}.conf'
        pending_path = pending_user_dir(server_name) / f'{username}.conf'

    elif config_type == 'stats':
        file_path = stats_cache_dir(server_name) / f'{username}.stats'
        pending_path = pending_stats_dir(server_name) / f'{username}.stats'

    else:
        raise ValueError('Invalid config type')

    lines = load_config(file_path)

    if not lines:
        ui.label('No server found').classes('text-red')
        return

    values = {
        line.key: line.value
        for line in lines
        if isinstance(line, Entry)
    }

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(file_path.name).classes('text-xl font-bold')

        for line in lines:
            if isinstance(line, Header):
                ui.separator()
                ui.label(line.name).classes('text-lg font-semibold')

            elif isinstance(line, Comment):
                ui.label(line.raw.lstrip('#')).classes('text-sm text-gray-500')

            elif isinstance(line, Entry):
                values[line.key] = ui.input(
                    label=line.key,
                    value=line.value
                ).classes('w-full')

        def save():
            resolved = {
                k: v.value if hasattr(v, 'value') else v
                for k, v in values.items()
            }
            text = serialize_config(lines, resolved)
            pending_path.write_text(text)
            ui.notify('Saved locally (pending upload)', type='positive')

        ui.button('Save', on_click=save).classes('mt-4')
