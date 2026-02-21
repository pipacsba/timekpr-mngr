# ui/config_editor.py
"""
Config editor UI.

Responsibilities:
- Render editable config forms
- Preserve formatting (comments, order)
- Save modified configs to pending uploads without extra blank lines
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from nicegui import app, ui

from storage import (
    server_cache_dir,
    user_cache_dir,
    stats_cache_dir,
    pending_dir,
    pending_user_dir,
    pending_stats_dir,
)
from ssh_sync import trigger_ssh_sync

import logging 
logger = logging.getLogger(__name__)


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


@dataclass
class ActivityMarker(Line):
    """Special marker for PlayTime activities insertion point"""
    pass


# -------------------------------------------------------------------
# Parsing & Serialization
# -------------------------------------------------------------------

def parse_config(text: str) -> List[Line]:
    lines: List[Line] = []

    for raw in text.splitlines():
        stripped = raw.strip()

        if stripped.startswith("##PLAYTIME_ACTIVITIES##"):
            lines.append(ActivityMarker(raw=raw))

        elif stripped.startswith('[') and stripped.endswith(']'):
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
            # Only add non-empty lines to keep the format tight
            if stripped:
                lines.append(Line(raw=raw))

    return lines


def serialize_config(lines: List[Line], values: Dict[str, str]) -> str:
    output: List[str] = []

    for line in lines:
        if isinstance(line, Entry):
            value = values.get(line.key, line.value)
            output.append(f'{line.key} = {value}')
        elif isinstance(line, ActivityMarker):
            output.append(line.raw)
        else:
            # Ensure no extra blank lines are preserved from Line objects
            raw_stripped = line.raw.strip()
            if raw_stripped:
                output.append(raw_stripped)

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
    if app.storage.user.get('is_admin', False):
        logger.info(f"config_editor.py render_config_editor is started.")
    
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
            ui.notify(f'No {config_type} found', type='warning', close_button='OK')
            return
    
        inputs: Dict[str, ui.input] = {}

        def save():
            resolved = {k: v.value for k, v in inputs.items()}
            content = serialize_config(lines, resolved)
            target.write_text(content)
            ui.notify('Saved locally (pending upload)', type='positive')
            trigger_ssh_sync()

        with ui.column().classes('w-full max-w-3xl'):
            ui.label(source.name).classes('text-xl font-bold mb-2')
            entries_container = ui.column().classes('w-full')
            
            def render_line(line, container):
                with container:
                    if isinstance(line, Header):
                        ui.separator()
                        ui.label(line.name).classes('text-lg font-semibold')
                    elif isinstance(line, Comment):
                        ui.label(line.raw).classes('text-sm text-gray-200')
                    elif isinstance(line, Entry):
                        inputs[line.key] = ui.input(label=line.key, value=line.value).classes('w-full')
                    elif isinstance(line, ActivityMarker):
                        ui.label(line.raw).classes('text-sm text-gray-200')

            # Initial render
            for line in lines:
                render_line(line, entries_container)

            # Add Activity logic
            if config_type == 'user':
                with ui.column().classes('w-full mt-4 p-4 border border-gray-700 rounded'):
                    ui.label("Add New PlayTime Activity Rule").classes('font-bold text-white')
                    with ui.row().classes('w-full items-center'):
                        mask_input = ui.input(label="Process Mask (Regexp)")
                        desc_input = ui.input(label="Description")
                        
                        def add_new_activity():
                            if not mask_input.value or not desc_input.value:
                                ui.notify("Please fill both fields", type='negative')
                                return
                            
                            existing = [int(l.key.split('_')[-1]) for l in lines 
                                        if isinstance(l, Entry) and l.key.startswith("PLAYTIME_ACTIVITY_")]
                            next_idx = max(existing, default=0) + 1
                            
                            new_key = f"PLAYTIME_ACTIVITY_{str(next_idx).zfill(3)}"
                            new_val = f"{mask_input.value}[{desc_input.value}]"
                            
                            new_entry = Entry(raw="", key=new_key, value=new_val)
                            
                            # Insert immediately after the marker
                            marker_pos = next((i for i, l in enumerate(lines) if isinstance(l, ActivityMarker)), len(lines))
                            lines.insert(marker_pos + 1, new_entry)
                            
                            # Update UI
                            render_line(new_entry, entries_container)
                            ui.notify(f"Added {new_key}")
                            mask_input.value = ''
                            desc_input.value = ''

                        ui.button(icon='add', on_click=add_new_activity).props('round color=primary')

            ui.button('Save Changes', on_click=save).classes('mt-6 w-full').props('color=primary')
    else:
        ui.label("No right to access page")


def add_user_extra_time(*, server_name: str, username: str, time_to_add_sec: int, playtime_to_add_sec: int):
    target = pending_stats_dir(server_name) / f'{username}.stats'
    lines = []
    a_sign = "+" if time_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add_sec)}"'))
    b_sign = "+" if playtime_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add_sec)}"'))
    
    # Empty values dict as these lines are not Entry objects
    target.write_text(serialize_config(lines, {}))
    ui.notify('Saved locally (pending upload)', type='positive')
    trigger_ssh_sync()
