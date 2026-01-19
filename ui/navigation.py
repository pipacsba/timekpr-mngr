"""
Slot-safe navigation for TimeKPR Manager
- Headers created inside page visits
- Supports multi-server and multi-user menus
- Fully compatible with NiceGUI >=1.16 and HA ingress
- Handles first-run: no servers / no users
"""

from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard


# -------------------------------------------------------------------
# Helper: build the common header inside page callbacks
# -------------------------------------------------------------------
def build_header():
    servers = load_servers()

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
# Page definitions
# -------------------------------------------------------------------

# Landing page (root)
def home_page():
    servers = load_servers()
    build_header()

    if not servers:
        ui.navigate.to('/welcome')
        return

    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
    ui.label('Manage server configuration, users, and statistics.')


# Welcome page (first-run, no servers)
def welcome_page():
    build_header()
    ui.label('Welcome to TimeKPR Manager').classes('text-3xl font-bold mb-4')
    ui.label('No servers configured yet.').classes('text-lg text-red-600')
    ui.label('Please add a server configuration to get started.').classes('text-gray-600')
    ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers')).props('unelevated').classes('mt-4')


# Servers list page
def servers_page_wrapper():
    build_header()
    servers_page()


# Server config page
def server_config_page(server_name: str):
    build_header()
    render_config_editor(server_name=server_name, config_type='server')


# User config page
def user_config_page(server_name: str, username: str):
    build_header()
    render_config_editor(server_name=server_name, config_type='user', username=username)


# Stats dashboard page
def stats_page(server_name: str, username: str):
    build_header()
    render_stats_dashboard(server_name=server_name, username=username)


# Fallback for missing server/user
def no_server_page():
    build_header()
    ui.label('No server found').classes('text-red text-2xl')
    ui.label('Please add a server configuration first.')
    ui.link('Go to Servers', '/servers')


# -------------------------------------------------------------------
# Route registration
# -------------------------------------------------------------------
def register_routes():
    """
    Register all NiceGUI pages.
    This must be called at app startup, after importing this module.
    """

    servers = load_servers()

    # Root
    ui.page('/', on_visit=home_page)

    # First-run / welcome page
    ui.page('/welcome', on_visit=welcome_page)

    # Servers list page
    ui.page('/servers', on_visit=servers_page_wrapper)

    # If no servers exist, register fallback routes
    if not servers:
        ui.page('/server/{server_name}', on_visit=no_server_page)
        ui.page('/server/{server_name}/user/{username}', on_visit=no_server_page)
        ui.page('/server/{server_name}/stats/{username}', on_visit=no_server_page)
        return

    # Otherwise, register per-server / per-user pages
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
