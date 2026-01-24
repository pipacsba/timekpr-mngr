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
from ssh_sync import trigger_ssh_sync

import logging 
logger = logging.getLogger(__name__)
logger.info(f"ui.config_editor.py is called at all")


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
  
    logger.info(f"config_editor.py render:config_editor is started.")

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
        
        ui.notify(f'No {config_type} found Maybe later?', type='warning', close_button='OK')
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
                    'text-sm text-gray-200'
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
            trigger_ssh_sync()

        ui.button('Save', on_click=save).classes('mt-4')

# -------------------------------------------------------------------
# Add extra time
# -------------------------------------------------------------------

def add_user_extra_time(
    *,
    server_name: str,
    username: str,
    time_to_add: int,
    playtime_to_add: int
):
    """
    timekpra --setplaytimeleft 'testuser' '+' '3600'
    timekpra --settimeleft 'testuser' '+' '3600'
    """
  
    logger.info(f"Additional time granting is started.")

    target = pending_stats_dir(server_name) / f'{username}.stats'

    lines = []
    a_sign = "+"
    if time_to_add < 0:
        a_sign = "-"
    logger.info(f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add)}"')
    lines.append(Line(
            raw = f'timekpra --settimeleft "{username}" "{a_sign}" "{abs(time_to_add)}"')
                )
    b_sign = "+"
    if playtime_to_add < 0:
        b_sign = "-"
    logger.info(f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add)}"')
    lines.append(Line(
            raw = f'timekpra --setplaytimeleft "{username}" "{b_sign}" "{abs(playtime_to_add)}"')
                )
    
    target.write_text(
        serialize_config(lines, {})
    )
    ui.notify(
        'Saved locally (pending upload)',
        type='positive',
    )
    trigger_ssh_sync()


def add_user_extra_time_via_config_file_but_it_is_not_used_as_aconfig_file_can_be_from_days_before(
    *,
    server_name: str,
    username: str,
    time_to_add: int,
    playtime_to_add: int
):
    """
    config_type: 'server' | 'user' | 'stats'
    """
  
    logger.info(f"Additional time granting is started.")

    source = stats_cache_dir(server_name) / f'{username}.stats'
    target = pending_stats_dir(server_name) / f'{username}.stats'

    lines = _load_config(source)

    if not lines:
        ui.notify('No config found for user. Maybe later?', type='warning', close_button='OK')
        return

    # Current values
    values: Dict[str, any] = {
        line.key: line.value
        for line in lines
        if isinstance(line, Entry)
    }

    if "TIME_SPENT_BALANCE" in values:
        values['TIME_SPENT_BALANCE'] = str(int(values['TIME_SPENT_BALANCE']) + time_to_add)
    else:
        ui.notify('TIME_SPENT_BALANCE is not in the config file!', type='warning', close_button='OK')
        return
    if "PLAYTIME_SPENT_BALANCE" in values:
        values['PLAYTIME_SPENT_BALANCE'] = str(int(values['PLAYTIME_SPENT_BALANCE']) + playtime_to_add)
    else:
        ui.notify('PLAYTIME_SPENT_BALANCE is not in the config file!', type='warning', close_button='OK')
        return

    target.write_text(
        serialize_config(lines, values)
    )
    ui.notify(
        'Saved locally (pending upload)',
        type='positive',
    )
    trigger_ssh_sync()
