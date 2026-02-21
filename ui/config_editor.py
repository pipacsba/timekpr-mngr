# ui/config_editor.py
"""
Config editor UI.
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
    pass

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
    existing_indices = []
    for line in lines:
        if isinstance(line, Entry) and line.key.startswith("PLAYTIME_ACTIVITY_"):
            try:
                existing_indices.append(int(line.key.split('_')[-1]))
            except: continue
    
    next_idx = max(existing_indices, default=0) + 1

    for line in lines:
        if isinstance(line, Entry):
            value = values.get(line.key, line.value)
            output.append(f'{line.key} = {value}')
        elif isinstance(line, ActivityMarker):
            output.append(line.raw)
            if new_activities:
                for act in new_activities:
                    key = f"PLAYTIME_ACTIVITY_{str(next_idx).zfill(3)}"
                    val = f"{act['mask']}[{act['desc']}]"
                    output.append(f"{key} = {val}")
                    next_idx += 1
        else:
            output.append(line.raw)
    return '\n'.join(output) + '\n'

def _load_config(path: Path) -> Optional[List[Line]]:
    if not path.exists(): return None
    return parse_config(path.read_text())

def render_config_editor(*, server_name: str, config_type: str, username: Optional[str] = None):
    if not app.storage.user.get('is_admin', False):
        ui.label("No right to access page")
        return

    # Initialize session storage for new activities if it doesn't exist
    if 'pending_activities' not in app.storage.user:
        app.storage.user['pending_activities'] = []

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
        ui.notify(f'No {config_type} found', type='warning')
        return

    values: Dict[str, ui.input] = {}

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(source.name).classes('text-xl font-bold mb-2')

        for line in lines:
            if isinstance(line, Header):
                ui.separator()
                ui.label(line.name).classes('text-lg font-semibold')
            elif isinstance(line, Comment):
                # Restored '#' display and original style
                ui.label(line.raw).classes('text-sm text-gray-200 italic')
            elif isinstance(line, Entry):
                values[line.key] = ui.input(label=line.key, value=line.value).classes('w-full')
            elif isinstance(line, ActivityMarker):
                ui.label(line.raw).classes('text-sm text-gray-200')
                ui.label("--- New Activities to be added ---").classes('text-blue-400 font-bold mt-2')

        if config_type == 'user':
            # STYLING FIX: Matching the original dark theme with border and proper contrast
            with ui.column().classes('w-full mt-4 p-4 border border-gray-600 rounded'):
                ui.label("Add New PlayTime Activity Rule").classes('font-bold text-white')
                with ui.row().classes('w-full items-center'):
                    mask_input = ui.input(label="Process Mask (Regexp)").classes('col-grow')
                    desc_input = ui.input(label="Description").classes('col-grow')
                    
                    def add_activity():
                        if mask_input.value and desc_input.value:
                            # Save to persistent storage
                            app.storage.user['pending_activities'].append({
                                'mask': mask_input.value,
                                'desc': desc_input.value
                            })
                            ui.notify(f"Added {desc_input.value} to list")
                            mask_input.value = ''
                            desc_input.value = ''
                        else:
                            ui.notify("Fill both fields", type='negative')

                    ui.button(icon='add', on_click=add_activity).props('round color=primary')

        def save():
            resolved = {k: w.value for k, w in values.items()}
            # Retrieve from persistent storage
            new_acts = app.storage.user.get('pending_activities', [])
            
            content = serialize_config(lines, resolved, new_acts)
            target.write_text(content)
            
            # Clear storage after successful save
            app.storage.user['pending_activities'] = []
            
            ui.notify('Saved locally (pending upload)', type='positive')
            trigger_ssh_sync()

        ui.button('Save Changes', on_click=save).classes('mt-6 w-full').props('color=primary')

# --- Helper for extra time ---
def add_user_extra_time(*, server_name: str, username: str, time_to_add_sec: int, playtime_to_add_sec: int):
    target = pending_stats_dir(server_name) / f'{username}.stats'
    lines = []
    
    a_sign = "+" if time_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add_sec)}"'))
    
    b_sign = "+" if playtime_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add_sec)}"'))
    
    target.write_text(serialize_config(lines, {}))
    ui.notify('Saved additional time', type='positive')
    trigger_ssh_sync()
