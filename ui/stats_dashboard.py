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

UNIFIED_CARD_WIDTH = 'w-full sm:w-48'
CHART_CARD_WIDTH = 'w-full sm:w-[450px]' # Wider for better display
FIXED_HEIGHT = 'h-[250px]' # Define a consistent height

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
    # Added h-full and justify-center
    with ui.card().classes(f'{UNIFIED_CARD_WIDTH} h-full text-center justify-center'):
        ui.icon(icon).classes('text-3xl text-primary')
        ui.label(title).classes('text-sm text-gray-500')
        ui.label(value).classes('text-xl font-bold')


def _render_usage_history_chart(server_name: str, username: str):
    # Hide the Plotly modebar via CSS (the most reliable method)
    ui.add_head_html('<style>.modebar { display: none !important; }</style>')

    history = get_user_history(server_name, username)
    if not history:
        ui.label('No data').classes('text-gray p-4 text-xs')
        return

    raw_dates = list(history.keys())
    
    # POLISH: Shorten dates (e.g., "2026-02-03" -> "03 Feb")
    formatted_dates = []
    for d in raw_dates:
        try:
            formatted_dates.append(datetime.strptime(d, '%Y-%m-%d').strftime('%d %b'))
        except ValueError:
            formatted_dates.append(d) # Fallback if format differs

    time_spent = [x / 3600 for x in [history[d]["time_spent"] for d in raw_dates]]
    playtime_spent = [x / 3600 for x in [history[d]["playtime_spent"] for d in raw_dates]]

    fig = go.Figure()

    # " Time" Bar - Translucent Blue
    fig.add_bar(
        x=formatted_dates, 
        y=time_spent, 
        name=" Time",
        marker_color='rgba(56, 189, 248, 0.3)', 
        marker_line_width=0,
        hovertemplate='Total: %{y:.1f}h<extra></extra>'
    )
    
    # "PlayTime" Bar - Translucent Green
    fig.add_bar(
        x=formatted_dates, 
        y=playtime_spent, 
        name="PlayTime",
        marker_color='rgba(52, 211, 153, 0.7)',
        marker_line_width=0,
        hovertemplate='Play: %{y:.1f}h<extra></extra>'
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        bargap=0.4,       
        height=200, # Matches the visual height you want inside the card
        margin=dict(l=10, r=10, t=30, b=30), # Add some breathing room
        xaxis=dict(
            tickangle=0,          # Keep text horizontal for readability
            showgrid=False,
            showline=False,
            fixedrange=True,
            tickfont=dict(size=10, color="#94a3b8"),
            type='category'       # Ensures every date is shown as a label
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
            y=1.1,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#64748b")
        ),
        hovermode="x unified",
        dragmode=False,
    )

    # Render the chart and ensure height is fixed via CSS
    chart = ui.plotly(fig).classes("w-full").style('height: 180px; margin-top: 10px;')
    
    # Programmatic backup to hide modebar
    chart._props['config'] = {'displayModeBar': False}
    chart.update()


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
    with ui.row().classes(f'w-full flex-wrap gap-4 items-stretch justify-center md:justify-start'):
        
        # 1. Last Update Card
        with ui.column().classes(f'{UNIFIED_CARD_WIDTH} {FIXED_HEIGHT}'): # Wrapper to force height
             _stat_card('Last Update', stats['LAST_CHECKED'].strftime("%Y-%m-%d %H:%M"), 'clock')
    
        # 2. History Chart Card
        with ui.card().classes(f'{CHART_CARD_WIDTH} {FIXED_HEIGHT} p-0 overflow-hidden'):
            ui.label("Last 7 Days").classes('text-sm font-bold m-2 text-center')
            _render_usage_history_chart(server_name, username)

    with ui.row().classes('w-full flex-wrap gap-4 mt-4 justify-center md:justify-start'):
        # 3. Time Stats
        if 'TIME_SPENT_BALANCE' in stats:
            _stat_card('Balance Today', _seconds_to_human(stats['TIME_SPENT_BALANCE']), icon='scale')

        if 'TIME_SPENT_DAY' in stats:
            _stat_card('Total Today', _seconds_to_human(stats['TIME_SPENT_DAY']), icon='today')

        if 'TIME_SPENT_WEEK' in stats:
            _stat_card('Total Week', _seconds_to_human(stats['TIME_SPENT_WEEK']), icon='date_range')
        
        if 'TIME_SPENT_MONTH' in stats:
            _stat_card('Total Month', _seconds_to_human(stats['TIME_SPENT_MONTH']), icon='calendar_month')

    with ui.row().classes('w-full flex-wrap gap-4 mt-4 justify-center md:justify-start'):
        # 4. Playtime Stats
        if 'PLAYTIME_SPENT_BALANCE' in stats:
            _stat_card('Play Balance', _seconds_to_human(stats['PLAYTIME_SPENT_BALANCE']), icon='videogame_asset')

        if 'PLAYTIME_SPENT_DAY' in stats:
            _stat_card('Play Today', _seconds_to_human(stats['PLAYTIME_SPENT_DAY']), icon='sports_esports')

    # Optional raw view
    with ui.expansion('Raw stats').classes('w-auto mt-8'):
        for key, value in stats.items():
            ui.label(f'{key} = {value}').classes('break-all')
