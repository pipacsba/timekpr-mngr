# navigation.py
"""
Slot-safe navigation and routing for TimeKPR Manager
- Headers and menus created inside page callbacks
- Compatible with NiceGUI >=1.16
"""

from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard


# -------------------------------------------------------------------
# Helper: Header/Menu builder (slot-safe)
# -------------------------------------------------------------------
def build_header():
    servers = load_servers()

    # Top-level header must be inside page callback
    with ui.header().classes('items-center justify-between'):
        ui.label('TimeKPR').classes('text-lg font-bold')

        with ui.row().classes('items-center'):
            # Global links
            ui.link('Home', '/')
            ui.link('Servers', '/servers')

            # Server menus
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
                                    on_click=lambda s=server_name, u=username:
                                        ui.navigate.to(f'/server/{s}/user/{u}')
                                )
                                ui.menu_item(
                                    'Statistics',
                                    on_click=lambda s=server_name, u=username:
                                        ui.navigate.to(f'/server/{s}/stats/{u}')
                                )


# -------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------
def home_page():
    build_header()
    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
    ui.label('Manage server configuration, users, and statistics.')


def servers_page_wrapper():
    build_header()
    servers_page()


def server_config_page(server_name: str):
    build_header()
    render_config_editor(server_name=server_name, config_type='server')


def user_config_page(server_name: str, username: str):
    build_header()
    render_config_editor(server_name=server_name, config_type='user', username=username)


def stats_page(server_name: str, username: str):
    build_header()
    render_stats_dashboard(server_name=server_name, username=username)


def no_server_page():
    build_header()
    ui.label('No server found').classes('text-red text-2xl')
    ui.label('Please add a server configuration first.')
    ui.link('Go to Servers', '/servers')


# -------------------------------------------------------------------
# Register all routes (slot-safe)
# -------------------------------------------------------------------
def register_routes():
    servers = load_servers()

    # Home and servers pages
    ui.page('/', on_visit=home_page)
    ui.page('/servers', on_visit=servers_page_wrapper)

    # If no servers exist
    if not servers:
        ui.page('/server/{server_name}', on_visit=no_server_page)
        return

    # Server and user pages
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
