# ui/config_editor.py
"""
Config editor UI.

Responsibilities:
- Render editable config forms
- Preserve formatting (comments, order)
- Save modified configs to pending uploads
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


# -------------------------------------------------------------------
# Data model (UI-local, simple)
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
# Parsing helpers
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
            lines.append(
                Entry(
                    raw=raw,
                    key=key.strip(),
                    value=value.strip(),
                )
            )
        else:
            lines.append(Line(raw=raw))

    return lines


def serialize_config(lines: List[Line], values: Dict[str, str]) -> str:
    output: List[str] = []

    for line in lines:
        if isinstance(line, Entry):
            value = values.get(line.key, line.value)
            output.append(f'{line.key} = {value}')
        else:
            output.append(line.raw)

    return '\n'.join(output) + '\n'


# -------------------------------------------------------------------
# File loading
# -------------------------------------------------------------------

def _load_config(path: Path) -> Optional[List[Line]]:
    if not path.exists():
        return None
    return parse_config(path.read_text())


# -------------------------------------------------------------------
# UI renderer
# -------------------------------------------------------------------

def render_config_editor(
    *,
    server_name: str,
    config_type: str,
    username: Optional[str] = None,
):
    """
    config_type: 'server' | 'user' | 'stats'
    """

    # Resolve paths
    if config_type == 'server':
        source = server_cache_dir(server_name) / 'server.conf'
        target = pending_dir(server_name) / 'server.conf'

    elif config_type == 'user':
        source = user_cache_dir(server_name) / f'{username}.conf'
        target = pending_user_dir(server_name) / f'{username}.conf'

    elif config_type == 'stats':
        source = stats_cache_dir(server_name) / f'{username}.stats'
        target = pending_stats_dir(server_name) / f'{username}.stats'

    else:
        raise ValueError('Invalid config type')

    lines = _load_config(source)

    if not lines:
        ui.label('No server found').classes('text-red text-lg')
        return

    # Current values
    values: Dict[str, any] = {
        line.key: line.value
        for line in lines
        if isinstance(line, Entry)
    }

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(source.name).classes('text-xl font-bold mb-2')

        for line in lines:
            if isinstance(line, Header):
                ui.separator()
                ui.label(line.name).classes('text-lg font-semibold')

            elif isinstance(line, Comment):
                ui.label(line.raw.lstrip('#')).classes(
                    'text-sm text-gray-500'
                )

            elif isinstance(line, Entry):
                values[line.key] = ui.input(
                    label=line.key,
                    value=line.value,
                ).classes('w-full')

        def save():
            resolved = {
                key: widget.value
                if hasattr(widget, 'value')
                else widget
                for key, widget in values.items()
            }
            target.write_text(
                serialize_config(lines, resolved)
            )
            ui.notify(
                'Saved locally (pending upload)',
                type='positive',
            )

        ui.button('Save', on_click=save).classes('mt-4')
