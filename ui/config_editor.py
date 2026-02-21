# ui/config_editor.py
"""
Config editor UI.
Modified to support adding new PlayTime activities.
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

        if stripped == "##PLAYTIME_ACTIVITIES##":
            lines.append(ActivityMarker(raw=raw))
        elif stripped.startswith('[') and stripped.endswith(']'):
            lines.append(Header(raw=raw, name=stripped[1:-1]))
        elif stripped.startswith('#'):
            lines.append(Comment(raw=raw))
        elif '=' in raw:
            key, value = raw.split('=', 1)
            lines.append(Entry(raw=raw, key=key.strip(), value=value.strip()))
        else:
            lines.append(Line(raw=raw))
    return lines

def serialize_config(lines: List[Line], values: Dict[str, str], new_activities: List[Dict[str, str]] = None) -> str:
    output: List[str] = []
    
    # Calculate the next NNN index based on existing entries
    existing_indices = []
    for line in lines:
        if isinstance(line, Entry) and line.key.startswith("PLAYTIME_ACTIVITY_"):
            try:
                existing_indices.append(int(line.key.split('_')[-1]))
            except ValueError:
                pass
    
    next_idx = max(existing_indices, default=0) + 1

    for line in lines:
        if isinstance(line, Entry):
            value = values.get(line.key, line.value)
            output.append(f'{line.key} = {value}')
        
        elif isinstance(line, ActivityMarker):
            output.append(line.raw)
            # Insert new activities immediately after the marker if provided
            if new_activities:
                for act in new_activities:
                    key = f"PLAYTIME_ACTIVITY_{str(next_idx).zfill(3)}"
                    val = f"{act['mask']}[{act['desc']}]"
                    output.append(f"{key} = {val}")
                    next_idx += 1
        else:
            output.append(line.raw)

    return '\n'.join(output) + '\n'

# -------------------------------------------------------------------
# UI Renderer
# -------------------------------------------------------------------

def render_config_editor(*, server_name: str, config_type: str, username: Optional[str] = None):
    if not app.storage.user.get('is_admin', False):
        ui.label("No right to access page")
        return

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

    lines = _load_config(source) # _load_config is internal helper from original file
    if not lines:
        ui.notify(f'No {config_type} found', type='warning')
        return

    # To store new activities added during this session
    pending_new_activities = []

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(source.name).classes('text-xl font-bold mb-2')

        # Reactive container for the existing lines
        entry_container = ui.column().classes('w-full')
        
        with entry_container:
            values: Dict[str, ui.input] = {}
            for line in lines:
                if isinstance(line, Header):
                    ui.separator()
                    ui.label(line.name).classes('text-lg font-semibold')
                elif isinstance(line, Comment):
                    ui.label(line.raw.lstrip('#')).classes('text-sm text-gray-400 italic')
                elif isinstance(line, Entry):
                    values[line.key] = ui.input(label=line.key, value=line.value).classes('w-full')
                elif isinstance(line, ActivityMarker):
                    ui.label("--- PlayTime Activities Section ---").classes('text-blue-400 font-bold mt-4')

        # Section to add new activities (only for user config)
        if config_type == 'user':
            with ui.card().classes('w-full mt-4 bg-gray-100'):
                ui.label("Add New PlayTime Activity").classes('font-bold')
                with ui.row().classes('w-full items-center'):
                    mask_input = ui.input(label="Process Mask (e.g. steam.exe)").classes('col-grow')
                    desc_input = ui.input(label="Description").classes('col-grow')
                    
                    def add_activity():
                        if mask_input.value and desc_input.value:
                            pending_new_activities.append({
                                'mask': mask_input.value,
                                'desc': desc_input.value
                            })
                            ui.notify(f"Added {desc_input.value} to pending list")
                            mask_input.value = ''
                            desc_input.value = ''
                        else:
                            ui.notify("Please fill both fields", type='negative')

                    ui.button(icon='add', on_click=add_activity).props('round')

        def save():
            resolved_values = {key: widget.value for key, widget in values.items()}
            # Pass the new activities to the serializer
            content = serialize_config(lines, resolved_values, pending_new_activities)
            
            target.write_text(content)
            ui.notify('Saved locally (pending upload)', type='positive')
            trigger_ssh_sync() #

        ui.button('Save Changes', on_click=save).classes('mt-6 w-full').props('color=primary')

def _load_config(path: Path) -> Optional[List[Line]]:
    if not path.exists():
        return None
    return parse_config(path.read_text())
