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
# CONFIGURATION
# -------------------------------------------------------------------

# This ensures ALL cards (stats and chart) have exactly the same width behavior
# w-full: Full width on mobile
# sm:w-48: Fixed width (approx 192px) on desktop/tablet
UNIFIED_CARD_WIDTH = 'w-full sm:w-48'


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
    # Use the unified class here
    with ui.card().classes(f'{UNIFIED_CARD_WIDTH} text-center'):
        ui.icon(icon).classes('text-3xl text-primary')
        ui.label(title).classes('text-sm text-gray-500')
        ui.label(value).classes('text-xl font-bold')

import plotly.graph_objects as go

def _render_usage_history_chart(server_name: str, username: str):
    history = get_user_history(server_name, username)
    if not history:
        ui.label('No data').classes('text-gray p-4 text-xs')
        return

    dates = list(history.keys())
    time_spent = [x / 3600 for x in [history[d]["time_spent"] for d in dates]]
    playtime_spent = [x / 3600 for x in [history[d]["playtime_spent"] for d in dates]]

    fig = go.Figure()

    # Total Time - Cyan/Blue
    fig.add_bar(
        x=dates, 
        y=time_spent, 
        name="Total",
        marker_color='#0ea5e9', 
        marker_line_width=0,
        hovertemplate='%{y:.1f}h' # Clean hover format
    )
    # Active Playtime - Green/Emerald
    fig.add_bar(
        x=dates, 
        y=playtime_spent, 
        name="Active",
        marker_color='#10b981',
        marker_line_width=0,
        hovertemplate='%{y:.1f}h'
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        bargap=0.3,
        height=180,
        margin=dict(l=0, r=0, t=20, b=0), # Reduced to the bone
        
        xaxis=dict(
            tickangle=0,
            showgrid=False,
            showline=False,
            fixedrange=True,
            tickfont=dict(size=10, color="#64748b")
        ),
        yaxis=dict(
            showgrid=False, 
            showticklabels=False, 
            fixedrange=True,
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1, # Push it slightly above the chart area
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#94a3b8")
        ),
        hovermode="x unified", # Shows both bars in one tooltip like a pro dashboard
        dragmode=False,
        modebar_remove=['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']
    )

    # Note: .style() works on NiceGUI elements to inject raw CSS
    ui.plotly(fig).classes("w-full").style('height: 180px; margin-top: 10px;')
# -------------------------------------------------------------------
# Dashboard renderer
# -------------------------------------------------------------------

def render_stats_dashboard(server_name: str, username: str):
    logger.info(f"ui.stats_dashboard.py render_stats_dashboard generation is started")
    stats = _load_stats(server_name, username)

    ui.label(f'Statistics: {username.capitalize()}').classes('text-2xl font-bold mb-4')

    if not stats:
        ui.label('No statistics available').classes('text-red')
        return

    # MAIN GRID
    # We dump everything into one big "flex-wrap" container 
    # so they flow naturally like a grid of same-sized tiles.
    with ui.row().classes('w-full flex-wrap gap-4 mt-4 justify-center md:justify-start'):
        
        # 1. Last Update Card
        if 'LAST_CHECKED' in stats:
             _stat_card(
                'Last Update',
                stats['LAST_CHECKED'].strftime("%Y-%m-%d %H:%M"),
                icon='clock'
            )

        # 2. History Chart Card
        # Now uses UNIFIED_CARD_WIDTH instead of 'flex-1'
        with ui.card().classes(f'{UNIFIED_CARD_WIDTH} p-0 overflow-hidden'):
             # Smaller title to fit
            ui.label("Last 7 Days").classes('text-sm font-bold m-2 text-center')
            _render_usage_history_chart(server_name, username)

        # 3. Time Stats
        if 'TIME_SPENT_BALANCE' in stats:
            _stat_card('Balance Today', _seconds_to_human(stats['TIME_SPENT_BALANCE']), icon='scale')

        if 'TIME_SPENT_DAY' in stats:
            _stat_card('Total Today', _seconds_to_human(stats['TIME_SPENT_DAY']), icon='today')

        if 'TIME_SPENT_WEEK' in stats:
            _stat_card('Total Week', _seconds_to_human(stats['TIME_SPENT_WEEK']), icon='date_range')
        
        if 'TIME_SPENT_MONTH' in stats:
            _stat_card('Total Month', _seconds_to_human(stats['TIME_SPENT_MONTH']), icon='calendar_month')

        # 4. Playtime Stats
        if 'PLAYTIME_SPENT_BALANCE' in stats:
            _stat_card('Play Balance', _seconds_to_human(stats['PLAYTIME_SPENT_BALANCE']), icon='videogame_asset')

        if 'PLAYTIME_SPENT_DAY' in stats:
            _stat_card('Play Today', _seconds_to_human(stats['PLAYTIME_SPENT_DAY']), icon='sports_esports')

    # Optional raw view
    with ui.expansion('Raw stats').classes('w-full mt-8'):
        for key, value in stats.items():
            ui.label(f'{key} = {value}').classes('break-all')
