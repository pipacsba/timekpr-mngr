#ui.navigation.py
"""
Safe slot-based navigation for TimeKPR Manager
- Slot-safe, first-run aware
- Compatible with HA Ingress
- No automatic navigation redirects
"""

from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard

import logging
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Header builder
# -------------------------------------------------------------------
def build_header():
    servers = load_servers()
    logger.info(f"Building header for {len(servers)} servers")
    with ui.header():
        ui.label("TimeKPR Manager")

# -------------------------------------------------------------------
# Page callbacks
# -------------------------------------------------------------------
def home_page():
    build_header()
    servers = load_servers()

    ui.label("TimeKPR Configuration Manager").classes("text-3xl font-bold mb-4")
    ui.label("Manage server configuration, users, and statistics.")

    if not servers:
        ui.label("No servers configured yet.").classes("text-red-700 font-semibold mt-4")
        ui.button("Go to Servers", on_click=lambda: ui.navigate.to("/servers")).classes("mt-2")

def welcome_page():
    build_header()
    ui.label("Welcome to TimeKPR Manager").classes("text-3xl font-bold mb-4")
    ui.label("No servers configured yet.").classes("text-lg text-red-600")
    ui.button("Go to Servers", on_click=lambda: ui.navigate.to("/servers")).classes("mt-4")

def servers_page_wrapper():
    build_header()
    servers_page()

def server_config_page(server_name: str):
    build_header()
    render_config_editor(server_name=server_name, config_type="server")

def user_config_page(server_name: str, username: str):
    build_header()
    render_config_editor(server_name=server_name, config_type="user", username=username)

def stats_page(server_name: str, username: str):
    build_header()
    render_stats_dashboard(server_name=server_name, username=username)

def no_server_page():
    build_header()
    ui.label("No server found").classes("text-red-700 font-bold")
    ui.label("Please add a server configuration first.").classes("text-gray-600")
    ui.button("Go to Servers", on_click=lambda: ui.navigate.to("/servers")).classes("mt-2")

# -------------------------------------------------------------------
# Route registration
# -------------------------------------------------------------------
def register_routes():
    servers = load_servers()
    logger.info(f"Register routes for {len(servers)} servers")

    # Root / home
    ui.page("/", on_visit=home_page)

    # Optional first-run welcome
    ui.page("/welcome", on_visit=welcome_page)

    if servers:
        # Servers list page
        ui.page("/servers", on_visit=servers_page_wrapper)
        for server_name in servers:
            ui.page(f"/server/{server_name}", on_visit=lambda s=server_name: server_config_page(s))
            for username in list_users(server_name):
                ui.page(
                    f"/server/{server_name}/user/{username}",
                    on_visit=lambda s=server_name, u=username: user_config_page(s, u)
                )
                ui.page(
                    f"/server/{server_name}/stats/{username}",
                    on_visit=lambda s=server_name, u=username: stats_page(s, u)
                )
    else:
        ui.page("/server", on_visit=no_server_page)
