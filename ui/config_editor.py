# ui/config_editor.py
"""
Config editor UI.
Modified to support adding new PlayTime activities dynamically.
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

def serialize_config(lines: List[Line], values: Dict[str, str]) -> str:
    output: List[str] = []
    for line in lines:
        if isinstance(line, Entry):
            # Get current value from the UI widget or fallback to original
            value = values.get(line.key, line.value)
            output.append(f'{line.key} = {value}')
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

    lines = parse_config(source.read_text()) if source.exists() else []
    if not lines:
        ui.notify(f'No {config_type} found', type='warning')
        return

    # Dictionary to hold the UI input widgets
    inputs: Dict[str, ui.input] = {}

    def save():
        resolved_values = {k: v.value for k, v in inputs.items()}
        content = serialize_config(lines, resolved_values)
        target.write_text(content)
        ui.notify('Saved locally (pending upload)', type='positive')
        trigger_ssh_sync()

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(source.name).classes('text-xl font-bold mb-2')

        # Container where all entry lines are rendered
        entries_container = ui.column().classes('w-full')
        
        def render_line(line, container):
            with container:
                if isinstance(line, Header):
                    ui.separator()
                    ui.label(line.name).classes('text-lg font-semibold')
                elif isinstance(line, Comment):
                    ui.label(line.raw).classes('text-sm text-gray-200 italic')
                elif isinstance(line, Entry):
                    inputs[line.key] = ui.input(label=line.key, value=line.value).classes('w-full')
                elif isinstance(line, ActivityMarker):
                    ui.label(line.raw).classes('text-sm text-gray-200')

        # Initial render of all lines
        for line in lines:
            render_line(line, entries_container)

        # Section for adding new activities
        if config_type == 'user':
            with ui.column().classes('w-full mt-4 p-4 border border-gray-700 rounded'):
                ui.label("Add New PlayTime Activity Rule").classes('font-bold text-white')
                with ui.row().classes('w-full items-center'):
                    mask_input = ui.input(label="Process Mask (Regexp)")
                    desc_input = ui.input(label="Description")
                    
                    def add_new_activity():
                        if not mask_input.value or not desc_input.value:
                            ui.notify("Fill both fields", type='negative')
                            return
                        
                        # Calculate next NNN
                        existing = [int(l.key.split('_')[-1]) for l in lines 
                                    if isinstance(l, Entry) and l.key.startswith("PLAYTIME_ACTIVITY_")]
                        next_idx = max(existing, default=0) + 1
                        
                        new_key = f"PLAYTIME_ACTIVITY_{str(next_idx).zfill(3)}"
                        new_val = f"{mask_input.value}[{desc_input.value}]"
                        
                        # Create the new entry object
                        new_entry = Entry(raw="", key=new_key, value=new_val)
                        
                        # Insert into the logic list after the marker
                        marker_pos = next((i for i, l in enumerate(lines) if isinstance(l, ActivityMarker)), len(lines))
                        lines.insert(marker_pos + 1, new_entry)
                        
                        # Render it immediately in the UI
                        render_line(new_entry, entries_container)
                        
                        ui.notify(f"Added {new_key}")
                        mask_input.value = ''
                        desc_input.value = ''

                    ui.button(icon='add', on_click=add_new_activity).props('round color=primary')

        ui.button('Save Changes', on_click=save).classes('mt-6 w-full').props('color=primary')

# --- Original Helper ---
def add_user_extra_time(*, server_name: str, username: str, time_to_add_sec: int, playtime_to_add_sec: int):
    target = pending_stats_dir(server_name) / f'{username}.stats'
    lines = []
    a_sign = "+" if time_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add_sec)}"'))
    b_sign = "+" if playtime_to_add_sec >= 0 else "-"
    lines.append(Line(raw=f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add_sec)}"'))
    target.write_text(serialize_config(lines, {}))
    ui.notify('Saved locally (pending upload)', type='positive')
    trigger_ssh_sync()
