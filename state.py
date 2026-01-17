# app/state.py
"""
Global UI state for the Unified Config Manager.

This module is intentionally minimal.
Do NOT put business logic here.
"""

from typing import Optional

# Currently selected server name
current_server: Optional[str] = None

# Optional future extensions (kept here intentionally):
# current_user: Optional[str] = None
# current_role: Optional[str] = None
# last_sync_status: Optional[dict] = None
