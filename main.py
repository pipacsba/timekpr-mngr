# main.py
"""
TimeKPR Next: Full NiceGUI App

- Uvicorn deployment
- Slot-safe navigation
- Background SSH sync
"""

import threading
from nicegui import ui

from ui.navigation import build_navigation, register_routes
from ssh_sync import run_sync_loop

# ---------------------------------------------------------------
# Start background sync thread
# ---------------------------------------------------------------

def start_background_sync():
    """
    Start SSH sync in a daemon thread.
    Must not call any UI functions here.
    """
    threading.Thread(
        target=run_sync_loop,
        kwargs={'interval_seconds': 180},  # every 3 minutes
        daemon=True
    ).start()


# ---------------------------------------------------------------
# Initialize UI (slot-safe)
# ---------------------------------------------------------------

def setup_ui():
    """
    Register routes and build navigation header.
    Must be called in the main thread / active slot.
    """
    register_routes()
    build_navigation()


# ---------------------------------------------------------------
# Create the main NiceGUI app object
# ---------------------------------------------------------------

app = ui.create_app()

# ---------------------------------------------------------------
# Set up UI and start background sync before Uvicorn runs
# ---------------------------------------------------------------

# Initialize UI elements in the main thread / active slot
setup_ui()

# Start background sync thread
start_background_sync()


# ---------------------------------------------------------------
# Run with Uvicorn if invoked directly
# ---------------------------------------------------------------

if __name__ == '__main__':
    import uvicorn

    # Launch Uvicorn with the NiceGUI ASGI app
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        ws_max_size=200*1024*1024
    )
