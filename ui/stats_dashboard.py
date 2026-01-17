from nicegui import ui
from pathlib import Path
from storage import CACHE
from state import current_server

def parse_stats(path: Path):
    data = {}
    for line in path.read_text().splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            data[k.strip()] = int(v.strip())
    return data


@ui.page('/stats/{user}')
def stats_page(user: str):
    ui.label(f'Stats for {user}').classes('text-2xl font-bold')

    path = CACHE / current_server / 'stats' / f'{user}.conf'
    if not path.exists():
        ui.label('No stats available')
        return

    stats = parse_stats(path)

    ui.chart({
        'title': {'text': 'Usage Time'},
        'xAxis': {'type': 'category', 'data': list(stats.keys())},
        'yAxis': {'type': 'value'},
        'series': [{
            'type': 'bar',
            'data': list(stats.values())
        }]
    }).classes('w-full h-96')
