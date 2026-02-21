# ui/config_editor.py
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
    """Marker for ##PLAYTIME_ACTIVITIES##"""
    pass

def parse_config(text: str) -> List[Line]:
    lines = []
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
    output = []
    # Calculate next index
    existing_indices = []
    for line in lines:
        if isinstance(line, Entry) and line.key.startswith("PLAYTIME_ACTIVITY_"):
            try:
                existing_indices.append(int(line.key.split('_')[-1]))
            except ValueError: pass
    
    next_idx = max(existing_indices, default=0) + 1

    for line in lines:
        if isinstance(line, Entry):
            val = values.get(line.key, line.value)
            output.append(f'{line.key} = {val}')
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

def render_config_editor(*, server_name: str, config_type: str, username: Optional[str] = None):
    # ... (Original resolve logic here) ...
    if config_type == 'server':
        source = server_cache_dir(server_name) / 'server.conf'
        target = pending_dir(server_name) / 'server.conf'
    elif config_type == 'user':
        source = user_cache_dir(server_name) / f'{username}.conf'
        target = pending_user_dir(server_name) / f'{username}.conf'
    else:
        source = stats_cache_dir(server_name) / f'{username}.stats'
        target = pending_stats_dir(server_name) / f'{username}.stats'

    lines = parse_config(source.read_text()) if source.exists() else []
    pending_new = []

    with ui.column().classes('w-full max-w-3xl'):
        ui.label(f"Editing {source.name}").classes('text-xl font-bold')
        
        # Existing Entries
        entry_widgets = {}
        for line in lines:
            if isinstance(line, Header):
                ui.label(line.name).classes('text-lg font-bold mt-4')
            elif isinstance(line, Entry):
                entry_widgets[line.key] = ui.input(label=line.key, value=line.value).classes('w-full')
            elif isinstance(line, ActivityMarker):
                ui.separator()
                ui.label("PlayTime Rules").classes('text-blue-500 font-bold')

        # Add Activity Form
        if config_type == 'user':
            with ui.row().classes('w-full items-center bg-blue-50 p-2'):
                m = ui.input('Process Mask')
                d = ui.input('Description')
                ui.button(icon='add', on_click=lambda: (pending_new.append({'mask': m.value, 'desc': d.value}), 
                                                        ui.notify(f"Added {d.value}"), 
                                                        m.set_value(''), d.set_value('')))

        ui.button('Save', on_click=lambda: (
            target.write_text(serialize_config(lines, {k: w.value for k, w in entry_widgets.items()}, pending_new)),
            ui.notify('Saved!'),
            trigger_ssh_sync()
        )).classes('w-full mt-4')

# --- IMPORTANT: Keep the function that main.py/navigation.py expects ---
def add_user_extra_time(server_name: str, username: str, seconds: int):
    """Original helper used by the dashboard or quick-actions"""
    # ... your original implementation of this function ...
    pass
