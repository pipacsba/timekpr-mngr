# stats_history.py

import json
from datetime import date
from pathlib import Path
from typing import Dict

from storage import history_file

MAX_DAYS = 30

def _load(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save(path: Path, data: Dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def update_daily_usage(
    *,
    server: str,
    user: str,
    time_spent_day: int,
    playtime_spent_day: int,
) -> None:
    """
    Update rolling 30-day daily usage history.
    """
    path = history_file(server, user)
    history = _load(path)

    today = date.today().isoformat()
    history[today] = {
        "time_spent": time_spent_day,
        "playtime_spent": playtime_spent_day,
    }

    # prune old entries
    for d in sorted(history.keys())[:-MAX_DAYS]:
        history.pop(d, None)

    _save(path, history)
