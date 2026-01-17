# main.py
"""
TimeKPR Next: Full NiceGUI App

- Slot-safe UI
- Background SSH sync
- Uvicorn deployment
"""

import threading
from nicegui import ui, app as nicegui_app

from ui.navigation import build_navigation, register_routes
from ssh_sync import run_sync_loop


# ---------------------------------------------------------------
# Start background SSH sync
# ---------------------------------------------------------------

def start_background_sync():
    threading.Thread(
        target=run_sync_loop,
        kwargs={'interval_seconds': 180},
        daemon=True
    ).start()


# ---------------------------------------------------------------
# Slot-safe UI initialization
# ---------------------------------------------------------------

def setup_ui():
    register_routes()
    build_navigation()


# ---------------------------------------------------------------
# Initialize UI and start background sync
# ---------------------------------------------------------------

setup_ui()
start_background_sync()


# ---------------------------------------------------------------
# Run with Uvicorn if invoked directly
# ---------------------------------------------------------------

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        "main:nicegui_app",  # pass the ASGI app object
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024
    )
