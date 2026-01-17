# main.py
"""
TimeKPR Next: Full NiceGUI App

Responsibilities:
- Initialize app
- Start background SSH sync
- Build navigation
- Launch NiceGUI
"""

import threading
from nicegui import ui, run

from navigation import build_navigation, register_routes
from ssh_sync import run_sync_loop

# Optional: import state module if needed
# from state import app_state


# -------------------------------------------------------------------
# Start background sync thread
# -------------------------------------------------------------------

threading.Thread(
    target=run_sync_loop,
    kwargs={'interval_seconds': 180},  # every 3 minutes
    daemon=True
).start()


# -------------------------------------------------------------------
# Build UI navigation and routes
# -------------------------------------------------------------------

build_navigation()
register_routes()


# -------------------------------------------------------------------
# Launch NiceGUI server
# -------------------------------------------------------------------

if __name__ == '__main__':
    # Launch on default 127.0.0.1:8080
    run(title='TimeKPR Manager', favicon='🕒', reload=True)
