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
import plotly.graph_objects as go

from stats_history import get_user_history
from storage import stats_cache_dir

import logging 
logger = logging.getLogger(__name__)


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
        if not line:
            continue
        if line[0] in ["#", "["]:
            continue
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        try:
            stats[key] = int(value)
        except ValueError:
            if key == "LAST_CHECKED":
                try:
                    stats[key] = datetime.strptime(f"{value} UTC", time_format)
                except ValueError:
                    pass

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
    minutes, s = divmod(abs(seconds), 60)
    hours, m = divmod(minutes, 60)
    if seconds < 0 and hours > 0:
        hours = 0 - hours
    elif seconds < 0:
        m = 0 - m
    return f'{hours}h {m}m'


def _stat_card(title: str, value: str, icon: str):
    with ui.card().classes('w-48 text-center'):
        ui.icon(icon).classes('text-3xl text-primary')
        ui.label(title).classes('text-sm text-gray-500')
        ui.label(value).classes('text-xl font-bold')

def _render_usage_history_chart(server_name: str, username: str):
    history = get_user_history(server_name, username)
    if not history:
        ui.label('No historical data available').classes('text-gray')
        return

    dates = list(history.keys())
    # Convert seconds to hours for cleaner Y-axis numbers
    time_spent = [x / 3600 for x in [history[d]["time_spent"] for d in dates]]
    playtime_spent = [x / 3600 for x in [history[d]["playtime_spent"] for d in dates]]
    
    fig = go.Figure()

    fig.add_bar(
        x=dates,
        y=time_spent,
        name="Time [h]",
    )

    fig.add_bar(
        x=dates,
        y=playtime_spent,
        name="Playtime [h]",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",  
        barmode="group",
        height=300, # Increased height slightly for touch targets
        margin=dict(l=10, r=10, t=20, b=10), # Tight margins for mobile
        xaxis=dict(
            tickangle=-45, # Slant labels to fit narrow screens
            automargin=True
        ),
        yaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)'
        ),
        # Legend at bottom prevents overlapping the chart on narrow screens
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.3, 
            xanchor="center", 
            x=0.5
        ),
        # CRITICAL FOR PHONES: Prevents chart from hijacking page scroll
        dragmode=False 
    )

    # config={'responsive': True} helps Plotly resize when phone orientation changes
    ui.plotly(fig).classes("w-full h-full").config({'displayModeBar': False, 'responsive': True})


# -------------------------------------------------------------------
# Dashboard renderer
# -------------------------------------------------------------------

def render_stats_dashboard(server_name: str, username: str):
    logger.info(f"ui.stats_dashboard.py render_stats_dashboard generation is started")
    stats = _load_stats(server_name, username)

    ui.label(f'Statistics: {username.capitalize()}').classes(
        'text-2xl font-bold mb-4'
    )

    if not stats:
        ui.label('No statistics available').classes('text-red')
        return

    # 1. Top Section: Last Update + History Chart
    # flex-wrap allows items to stack on mobile
    with ui.row().classes('w-full flex-wrap gap-4 mt-4 items-stretch'):
        
        # Last Checked (Left or Top)
        if 'LAST_CHECKED' in stats:
            with ui.column().classes('w-full md:w-auto'):
                 _stat_card(
                    'Last Update',
                    stats['LAST_CHECKED'].strftime("%Y-%m-%d %H:%M"),
                    icon='clock'
                )

        # Chart (Right or Bottom, takes remaining space)
        with ui.card().classes('w-full md:flex-1 min-h-[350px]'):
            ui.label("Last 7 Days").classes('text-lg font-bold mb-2')
            _render_usage_history_chart(server_name, username)
    
    # 2. Stats Cards
    # Using justify-center allows cards to look good if there are few of them
    with ui.row().classes('w-full flex-wrap gap-4 mt-6 justify-center md:justify-start'):     
        if 'TIME_SPENT_BALANCE' in stats:
            _stat_card(
                'Balance Today',
                _seconds_to_human(stats['TIME_SPENT_BALANCE']),
                icon='scale'
            )

        if 'TIME_SPENT_DAY' in stats:
            _stat_card(
                'Total Today',
                _seconds_to_human(stats['TIME_SPENT_DAY']),
                icon='today'
            )

        if 'TIME_SPENT_WEEK' in stats:
            _stat_card(
                'Total Week',
                _seconds_to_human(stats['TIME_SPENT_WEEK']),
                icon='date_range'
            )
        
        if 'TIME_SPENT_MONTH' in stats:
            _stat_card(
                'Total Month',
                _seconds_to_human(stats['TIME_SPENT_MONTH']),
                icon='calendar_month'
            )

    # 3. Playtime Specifics (New Row)
    has_playtime = 'PLAYTIME_SPENT_BALANCE' in stats or 'PLAYTIME_SPENT_DAY' in stats
    
    if has_playtime:
        ui.label("Playtime Breakdown").classes('text-xl font-bold mt-8 mb-2')
        with ui.row().classes('w-full flex-wrap gap-4 justify-center md:justify-start'):
            if 'PLAYTIME_SPENT_BALANCE' in stats:
                _stat_card(
                    'Playtime Balance',
                    _seconds_to_human(stats['PLAYTIME_SPENT_BALANCE']),
                    icon='videogame_asset'
                )

            if 'PLAYTIME_SPENT_DAY' in stats:
                _stat_card(
                    'Playtime Today',
                    _seconds_to_human(stats['PLAYTIME_SPENT_DAY']),
                    icon='sports_esports'
                )

    # Optional raw view
    with ui.expansion('Raw stats').classes('w-full mt-8'):
        for key, value in stats.items():
            # break-all prevents long strings from pushing the layout width out
            ui.label(f'{key} = {value}').classes('break-all')
