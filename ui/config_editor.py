# ui/config_editor.py
"""
Config editor UI.

Responsibilities:
- Render editable config forms
- Preserve formatting (comments, order)
- Save modified configs to pending uploads
- Support adding new PlayTime activities
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

@dataclass
class ActivityMarker(Line):
    """Special marker for PlayTime activities insertion point"""
    pass


# -------------------------------------------------------------------
# Parsing helpers
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


def serialize_config(lines: List[Line], values: Dict[str, str], new_activities: List[Dict[str, str]] = None) -> str:
    output: List[str] = []
    
    # Determine the next available NNN index for new activities
    existing_indices = []
    for line in lines:
        if isinstance(line, Entry) and line.key.startswith("PLAYTIME_ACTIVITY_"):
            try:
                idx_str = line.key.split('_')[-1]
                existing_indices.append(int(idx_str))
            except (ValueError, IndexError):
                continue
    
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
            ui.notify(f'No {config_type} found Maybe later?', type='warning', close_button='OK')
            return
    
        values: Dict[str, any] = {}
        pending_new_activities = []
    
        with ui.column().classes('w-full max-w-3xl'):
            ui.label(source.name).classes('text-xl font-bold mb-2')
    
            for line in lines:
                if isinstance(line, Header):
                    ui.separator()
                    ui.label(line.name).classes('text-lg font-semibold')
    
                elif isinstance(line, Comment):
                    # Restored original styling: showing # and using text-gray-200
                    ui.label(line.raw).classes('text-sm text-gray-200')
    
                elif isinstance(line, Entry):
                    values[line.key] = ui.input(
                        label=line.key,
                        value=line.value,
                    ).classes('w-full')
                
                elif isinstance(line, ActivityMarker):
                    ui.label(line.raw).classes('text-sm text-gray-200')
                    ui.label("--- New Activities Pending Save ---").classes('text-blue-400 font-bold mt-2')

            # Add activity section for user configurations
            if config_type == 'user':
                # Replaced greyish card with transparent container to match original theme visibility
                with ui.column().classes('w-full mt-4 p-4 border border-gray-700 rounded'):
                    ui.label("Add New PlayTime Activity Rule").classes('font-bold text-white')
                    with ui.row().classes('w-full items-center'):
                        mask_input = ui.input(label="Process Mask (Regexp)").classes('col-grow')
                        desc_input = ui.input(label="Description").classes('col-grow')
                        
                        def add_activity_to_list():
                            if mask_input.value and desc_input.value:
                                pending_new_activities.append({
                                    'mask': mask_input.value,
                                    'desc': desc_input.value
                                })
                                ui.notify(f"Queued: {desc_input.value}")
                                mask_input.value = ''
                                desc_input.value = ''
                            else:
                                ui.notify("Please provide both mask and description", type='negative')

                        ui.button(icon='add', on_click=add_activity_to_list).props('round color=primary')

            def save():
                resolved = {
                    key: widget.value
                    if hasattr(widget, 'value')
                    else widget
                    for key, widget in values.items()
                }
                
                content = serialize_config(lines, resolved, pending_new_activities)
                target.write_text(content)
                ui.notify('Saved locally (pending upload)', type='positive')
                trigger_ssh_sync()
    
            ui.button('Save Changes', on_click=save).classes('mt-6 w-full').props('color=primary')
    else:
        ui.label("No right to access page")
        
# -------------------------------------------------------------------
# Add extra time
# -------------------------------------------------------------------

def add_user_extra_time(
    *,
    server_name: str,
    username: str,
    time_to_add_sec: int,
    playtime_to_add_sec: int
):
    target = pending_stats_dir(server_name) / f'{username}.stats'
    lines = []
    
    a_sign = "+" if time_to_add_sec >= 0 else "-"
    logger.debug(f'Command: timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add_sec)}"')
    lines.append(Line(raw=f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add_sec)}"'))
    
    b_sign = "+" if playtime_to_add_sec >= 0 else "-"
    logger.debug(f'Command: timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add_sec)}"')
    lines.append(Line(raw=f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add_sec)}"'))
    
    target.write_text(serialize_config(lines, {}))
    ui.notify('Saved locally (pending upload)', type='positive')
    trigger_ssh_sync()
    logger.info(f'Additional time is granted to {username}')
