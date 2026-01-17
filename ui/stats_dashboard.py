# ui/stats_dashboard.py
"""
User statistics dashboard UI.

Responsibilities:
- Load cached stats files
- Parse simple KEY = VALUE metrics
- Render visual dashboard cards
"""

from typing import Dict
from nicegui import ui

from storage import stats_cache_dir


# -------------------------------------------------------------------
# Parsing helpers
# -------------------------------------------------------------------

def _parse_stats(text: str) -> Dict[str, float]:
    """
    Simple stats parser:
    KEY = VALUE
    """
    stats: Dict[str, float] = {}

    for line in text.splitlines():
        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        try:
            stats[key] = float(value)
        except ValueError:
            continue

    return stats


def _load_stats(server_name: str, username: str) -> Dict[str, float]:
    path = stats_cache_dir(server_name) / f'{username}.stats'
    if not path.exists():
        return {}
    return _parse_stats(path.read_text())


# -------------------------------------------------------------------
# UI helpers
# -------------------------------------------------------------------

def _seconds_to_human(seconds: float) -> str:
    seconds = int(seconds)
    minutes, s = divmod(seconds, 60)
    hours, m = divmod(minutes, 60)
    return f'{hours}h {m}m'


def _stat_card(title: str, value: str, icon: str):
    with ui.card().classes('w-48 text-center'):
        ui.icon(icon).classes('text-3xl text-primary')
        ui.label(title).classes('text-sm text-gray-500')
        ui.label(value).classes('text-xl font-bold')


# -------------------------------------------------------------------
# Dashboard renderer
# -------------------------------------------------------------------

def render_stats_dashboard(server_name: str, username: str):
    stats = _load_stats(server_name, username)

    ui.label(f'Statistics: {username}').classes(
        'text-2xl font-bold mb-4'
    )

    if not stats:
        ui.label('No statistics available').classes('text-red')
        return

    with ui.row().classes('gap-6 mb-6'):
        if 'TOTAL_TIME' in stats:
            _stat_card(
                'Total Time',
                _seconds_to_human(stats['TOTAL_TIME']),
                icon='timeline',
            )

        if 'TODAY_TIME' in stats:
            _stat_card(
                'Today',
                _seconds_to_human(stats['TODAY_TIME']),
                icon='today',
            )

        if 'WEEK_TIME' in stats:
            _stat_card(
                'This Week',
                _seconds_to_human(stats['WEEK_TIME']),
                icon='date_range',
            )

    # Optional raw view for debugging
    with ui.expansion('Raw stats'):
        for key, value in stats.items():
            ui.label(f'{key} = {value}')
