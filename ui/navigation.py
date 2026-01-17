# navigation.py
"""
Application navigation and routing (slot-safe).

Responsibilities:
- Top navigation bar
- Page routing
- Wiring UI pages together
"""

from nicegui import ui

from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard


# -------------------------------------------------------------------
# Fallback pages
# -------------------------------------------------------------------

def _no_server_page():
    ui.label('No server found').classes('text-red text-2xl')
    ui.label('Please add a server configuration first.')
    ui.link('Go to Servers', '/servers')


# -------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------

def home_page():
    ui.label('TimeKPR Configuration Manager').classes(
        'text-3xl font-bold mb-4'
    )
    ui.label(
        'Manage server configuration, users, and statistics.'
    )


def server_config_page(server_name: str):
    render_config_editor(
        server_name=server_name,
        config_type='server',
    )


def user_config_page(server_name: str, username: str):
    render_config_editor(
        server_name=server_name,
        config_type='user',
        username=username,
    )


def stats_page(server_name: str, username: str):
    render_stats_dashboard(
        server_name=server_name,
        username=username,
    )


# -------------------------------------------------------------------
# Header / navigation bar (slot-safe)
# -------------------------------------------------------------------

def build_navigation():
    """
    Build top header and menus inside the main UI slot.
    Must be called after NiceGUI is running.
    """
    servers = load_servers()

    # Wrap in a container slot to avoid "slot stack is empty" errors
    with ui.row().classes('w-full'):
        with ui.header().classes('items-center justify-between'):
            ui.label('TimeKPR').classes('text-lg font-bold')

            with ui.row().classes('items-center'):
                ui.link('Home', '/')
                ui.link('Servers', '/servers')

                if not servers:
                    return

                # Server menus
                for server_name in servers:
                    with ui.menu(server_name):
                        ui.menu_item(
                            'Server config',
                            on_click=lambda s=server_name:
                            ui.navigate.to(f'/server/{s}')
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
# Route registration
# -------------------------------------------------------------------

def register_routes():
    ui.page('/', on_visit=home_page)
    ui.page('/servers', on_visit=servers_page)

    servers = load_servers()

    if not servers:
        ui.page('/server/{server_name}', on_visit=_no_server_page)
        return

    for server_name in servers:
        ui.page(
            f'/server/{server_name}',
            on_visit=lambda s=server_name: server_config_page(s),
        )

        for username in list_users(server_name):
            ui.page(
                f'/server/{server_name}/user/{username}',
                on_visit=lambda s=server_name, u=username:
                user_config_page(s, u),
            )

            ui.page(
                f'/server/{server_name}/stats/{username}',
                on_visit=lambda s=server_name, u=username:
                stats_page(s, u),
            )
