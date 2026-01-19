#ui/navigation.py
"""
Safe slot-based navigation for TimeKPR Manager
- Fully slot-safe
- Handles first-run (no servers / no users)
- Compatible with HA Ingress
- No automatic navigation redirects to avoid endless loops
"""

from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard

import logging
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Helper: build the top header inside page callbacks
# -------------------------------------------------------------------
def build_header():
    servers = load_servers()
    logger.info(f"Building header for {len(servers)} servers")

    with ui.header().classes('items-center justify-between bg-primary text-white'):
        ui.label('TimeKPR').classes('text-lg font-bold')
        with ui.row().classes('items-center'):
            ui.link('Home', '/')
            ui.link('Servers', '/servers')

            # Multi-server menus
            for server_name in servers:
                with ui.menu(server_name):
                    ui.menu_item(
                        'Server config',
                        on_click=lambda s=server_name: ui.navigate.to(f'/server/{s}')
                    )

                    users = list_users(server_name)
                    if users:
                        ui.separator()
                        for username in users:
                            with ui.menu(username):
                                ui.menu_item(
                                    'Config',
                                    on_click=lambda s=server_name, u=username: ui.navigate.to(f'/server/{s}/user/{u}')
                                )
                                ui.menu_item(
                                    'Statistics',
                                    on_click=lambda s=server_name, u=username: ui.navigate.to(f'/server/{s}/stats/{u}')
                                )


# -------------------------------------------------------------------
# Page callbacks
# -------------------------------------------------------------------

def home_page():
    """Landing page"""
    build_header()
    logger.info(f"Headers built for home_page")
    servers = load_servers()

    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
    ui.label('Manage server configuration, users, and statistics.')

    if not servers:
        ui.label('No servers configured yet.').classes('text-red-700 font-semibold mt-4')
        ui.label('Please go to the Servers page to add your first server.').classes('text-gray-600 mt-1')
        ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers')).classes('mt-2')


def welcome_page():
    """First-run welcome page (not auto-navigated to)"""
    build_header()
    logger.info(f"Headers built for welcome_page")
    ui.label('Welcome to TimeKPR Manager').classes('text-3xl font-bold mb-4')
    ui.label('No servers configured yet.').classes('text-lg text-red-600')
    ui.label('Please add a server configuration to get started.').classes('text-gray-600')
    ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers')).props('unelevated').classes('mt-4')


def servers_page_wrapper():
    build_header()
    logger.info(f"Headers built for servers_page")
    servers_page()


def server_config_page(server_name: str):
    build_header()
    logger.info(f"Headers built for server config page")
    render_config_editor(server_name=server_name, config_type='server')


def user_config_page(server_name: str, username: str):
    build_header()
    logger.info(f"Headers built for user config page")
    render_config_editor(server_name=server_name, config_type='user', username=username)


def stats_page(server_name: str, username: str):
    build_header()
    logger.info(f"Headers built for stats page")
    render_stats_dashboard(server_name=server_name, username=username)


def no_server_page():
    build_header()
    logger.info(f"Headers built for no server page")
    ui.label('No server found').classes('text-red-700 font-bold')
    ui.label('Please add a server configuration first.').classes('text-gray-600')
    ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers')).classes('mt-2')


# -------------------------------------------------------------------
# Register routes
# -------------------------------------------------------------------
def register_routes():
    servers = load_servers()
    logger.info(f"Register routes for {len(servers)} servers")

    # Root / home
    ui.page('/', on_visit=home_page)

    # Welcome page (optional first-run)
    ui.page('/welcome', on_visit=welcome_page)

    # Dynamic server/user pages
    if servers:
    # Servers list page
        ui.page('/servers', on_visit=servers_page_wrapper)
        logger.info(f"if servers passed for {len(servers)} servers")
        for server_name in servers:
            ui.page(f'/server/{server_name}', on_visit=lambda s=server_name: server_config_page(s))
            for username in list_users(server_name):
                ui.page(
                    f'/server/{server_name}/user/{username}',
                    on_visit=lambda s=server_name, u=username: user_config_page(s, u)
                )
                ui.page(
                    f'/server/{server_name}/stats/{username}',
                    on_visit=lambda s=server_name, u=username: stats_page(s, u)
                )
    else:
        logger.info("No servers configured, registering fallback page")
        ui.page('/server', on_visit=no_server_page)
