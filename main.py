# main.py
"""
TimeKPR Next
- Slot-safe NiceGUI
- Background SSH sync
- Uvicorn deployment
"""

import threading
from nicegui import app as nicegui_app
from ui.navigation import register_routes
from ssh_sync import run_sync_loop


# -------------------------------------------------------------------
# Initialize UI
# -------------------------------------------------------------------
# Routes are registered; headers/menus are created inside page callbacks
register_routes()


# -------------------------------------------------------------------
# Start background SSH sync in a daemon thread
# -------------------------------------------------------------------
threading.Thread(
    target=run_sync_loop,
    kwargs={'interval_seconds': 180},  # every 3 minutes
    daemon=True
).start()


# -------------------------------------------------------------------
# Expose ASGI app for Uvicorn
# -------------------------------------------------------------------
app = nicegui_app

# -------------------------------------------------------------------
# Optional: run with Python directly (development)
# -------------------------------------------------------------------
if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024
    )
