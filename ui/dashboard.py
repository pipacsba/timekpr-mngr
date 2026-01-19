# ui/dashboard.py
"""
User statistics dashboards.

Responsibilities:
- Read cached stats files
- Parse basic metrics
- Render visual dashboards with NiceGUI
"""

from pathlib import Path
from typing import Dict

from nicegui import ui

from storage import stats_cache_dir

import logging 
logger = logging.getLogger(__name__)
logger.info(f"ui.dashboard.py is called at all")


# -------------------------------------------------------------------
# Stats parsing (simple, extensible)
# -------------------------------------------------------------------

def parse_stats(text: str) -> Dict[str, float]:
    """
    Very simple KEY = VALUE stats parser.
    Unknown lines are ignored.

    Example:
        TOTAL_TIME = 12345
        TODAY_TIME = 3600
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


def load_user_stats(server_name: str, username: str) -> Dict[str, float]:
    path = stats_cache_dir(server_name) / f'{username}.stats'
    if not path.exists():
        return {}
    return parse_stats(path.read_text())


# -------------------------------------------------------------------
# UI helpers
# -------------------------------------------------------------------

def _stat_card(title: str, value: str, icon: str = 'schedule'):
    with ui.card().classes('w-48 text-center'):
        ui.icon(icon).classes('text-3xl text-primary')
        ui.label(title).classes('text-sm text-gray-500')
        ui.label(value).classes('text-xl font-bold')


def _seconds_to_human(seconds: float) -> str:
    minutes, s = divmod(int(seconds), 60)
    hours, m = divmod(minutes, 60)
    return f'{hours}h {m}m'


# -------------------------------------------------------------------
# Dashboard
# -------------------------------------------------------------------

def render_dashboard(server_name: str, username: str):
    logger.info(f"ui.dashboard.py render_dashboard is started")
    stats = load_user_stats(server_name, username)

    if not stats:
        ui.label('No statistics available').classes('text-red')
        return

    ui.label(f'Statistics for {username}').classes('text-2xl font-bold')

    with ui.row().classes('gap-6 mt-4'):
        if 'TOTAL_TIME' in stats:
            _stat_card(
                'Total Time',
                _seconds_to_human(stats['TOTAL_TIME']),
                icon='timeline'
            )

        if 'TODAY_TIME' in stats:
            _stat_card(
                'Today',
                _seconds_to_human(stats['TODAY_TIME']),
                icon='today'
            )

        if 'WEEK_TIME' in stats:
            _stat_card(
                'This Week',
                _seconds_to_human(stats['WEEK_TIME']),
                icon='date_range'
            )

    # Optional raw view
    with ui.expansion('Raw stats'):
        for k, v in stats.items():
            ui.label(f'{k} = {v}')

