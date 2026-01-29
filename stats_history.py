# stats_history.py

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict

from storage import history_file

import logging 
logger = logging.getLogger(__name__)

MAX_DAYS = 30

def _load(path: Path) -> Dict[str, dict]:
    if not path.exists():
        logger.info(f"History stats file not found at {path}")
        return {}
    try:
        logger.info("Histoy stats file is being read")
        return json.loads(path.read_text())
    except Exception:
        logger.info(f"History stats file read error at {path}")
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

def get_user_history(server: str, user: str) -> dict[str, dict]:
    """
    Returns a date-indexed history for a user with gaps filled.
    {
        "YYYY-MM-DD": {
            "time_spent": int,
            "playtime_spent": int
        }
    }
    """
    
    path = history_file(server, user)
    raw_history = _load(path)

    if not raw_history:
        loggel.warning("No history stats read returned empty")
        return {}

    # Parse available dates
    parsed_dates = sorted(
        datetime.strptime(d, "%Y-%m-%d").date()
        for d in raw_history.keys()
    )

    start_date = parsed_dates[0]
    end_date = date.today()

    filled_history: dict[str, dict] = {}

    current = start_date
    while current <= end_date:
        key = current.isoformat()

        if key in raw_history:
            filled_history[key] = {
                "time_spent": int(raw_history[key].get("time_spent", 0)),
                "playtime_spent": int(raw_history[key].get("playtime_spent", 0)),
            }
        else:
            filled_history[key] = {
                "time_spent": 0,
                "playtime_spent": 0,
            }

        current += timedelta(days=1)

    return filled_history
