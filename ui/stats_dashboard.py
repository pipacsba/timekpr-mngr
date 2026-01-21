# ui/stats_dashboard.py
"""
User statistics dashboard UI.

Responsibilities:
- Load cached stats files
- Parse simple KEY = VALUE metrics
- Render visual dashboard cards
"""

from pathlib import Path
from typing import Dict
from datetime import datetime
from nicegui import ui

from storage import stats_cache_dir

import logging 
logger = logging.getLogger(__name__)
logger.info(f"ui.stats_dashboard.py is called at all")


# -------------------------------------------------------------------
# Parsing helpers
# -------------------------------------------------------------------

def _parse_stats(text: str) -> Dict[str, float]:
    """
    Very simple KEY = VALUE stats parser.
    Unknown lines are ignored.

    Example:
        TOTAL_TIME = 12345
        TODAY_TIME = 3600
    """
    stats: Dict[str, float] = {}
    time_format = '%Y-%m-%d %H:%M:%S %Z'

    for line in text.splitlines():
        if line[0] in ["#", "["]
            continue
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        try:
            stats[key] = float(value)
        except ValueError:
            if key == "LAST_CHECKED"
                stats[key] = datetime.strptime(f"{value} UTC", format)

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
    logger.info(f"ui.stats_dashboard.py render_stats_dashboard generation is started")
    stats = _load_stats(server_name, username)

    ui.label(f'Statistics: {username}').classes(
        'text-2xl font-bold mb-4'
    )

    if not stats:
        ui.label('No statistics available').classes('text-red')
        return

    with ui.row().classes('gap-6 mt-4'):
        if 'LAST_CHECKED' in stats:
            _stat_card(
                'last update time of the file',
                stats['LAST_CHECKED'],
                icon='clock'
            )

        
        if 'TIME_SPENT_BALANCE' in stats:
            _stat_card(
                'total time balance spent for this day',
                _seconds_to_human(stats['TIME_SPENT_BALANCE']),
                icon='today'
            )

        if 'TIME_SPENT_DAY' in stats:
            _stat_card(
                'total time spent for this day',
                _seconds_to_human(stats['TIME_SPENT_DAY']),
                icon='today'
            )

        if 'TIME_SPENT_WEEK' in stats:
            _stat_card(
                'total spent for this week',
                _seconds_to_human(stats['TIME_SPENT_WEEK']),
                icon='date_range'
            )
        
        if 'TIME_SPENT_MONTH' in stats:
            _stat_card(
                'total spent for this month',
                _seconds_to_human(stats['TIME_SPENT_MONTH']),
                icon='date_range'
            )

        if 'PLAYTIME_SPENT_BALANCE' in stats:
            _stat_card(
                'total PlayTime balance spent for this day',
                _seconds_to_human(stats['PLAYTIME_SPENT_BALANCE']),
                icon='today'
            )

        if 'PLAYTIME_SPENT_DAY' in stats:
            _stat_card(
                'total PlayTime spent for this day',
                _seconds_to_human(stats['PLAYTIME_SPENT_DAY']),
                icon='today'
            )

    # Optional raw view for debugging
    with ui.expansion('Raw stats'):
        for key, value in stats.items():
            ui.label(f'{key} = {value}')
