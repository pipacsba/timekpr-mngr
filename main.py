# main.py
"""
TimeKPR Next
- Slot-safe NiceGUI UI
- Background SSH sync
- Uvicorn deployment
"""

import threading
from nicegui import ui, app as nicegui_app

from ui.navigation import register_routes
from ssh_sync import run_sync_loop


# -------------------------------------------------------------------
# Start background SSH sync in a daemon thread
# -------------------------------------------------------------------
def start_background_sync():
    threading.Thread(
        target=run_sync_loop,
        kwargs={'interval_seconds': 180},  # every 3 minutes
        daemon=True
    ).start()


# -------------------------------------------------------------------
# Initialize UI (routes only)
# -------------------------------------------------------------------
def setup_ui():
    # Routes are registered; headers/menus are created per-page visit
    register_routes()


# -------------------------------------------------------------------
# Main execution
# -------------------------------------------------------------------
if __name__ == '__main__':
    import uvicorn

    # Setup UI (slot-safe)
    setup_ui()

    # Start background SSH sync
    start_background_sync()

    # Run via Uvicorn
    uvicorn.run(
        "main:nicegui_app",  # ASGI app
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024
    )
