# app/navigation.py
"""
Application navigation and page layout.

Responsibilities:
- Top-level navigation bar
- Page routing
- Context selection (server, user)
"""

from nicegui import ui

from servers import load_servers, list_users
from config_editor import render_editor


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _no_server_page():
    ui.label('No server found').classes('text-red text-xl')
    ui.label('Please configure a server first.')


# -------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------

def home_page():
    ui.label('TimeKPR Configuration Manager').classes('text-2xl font-bold')
    ui.label('Select a server from the menu to begin.')


def server_config_page(server_name: str):
    render_editor(
        server_name=server_name,
        config_type='server',
    )


def user_config_page(server_name: str, username: str):
    render_editor(
        server_name=server_name,
        config_type='user',
        username=username,
    )


def stats_page(server_name: str, username: str):
    render_editor(
        server_name=server_name,
        config_type='stats',
        username=username,
    )


# -------------------------------------------------------------------
# Navigation builder
# -------------------------------------------------------------------

def build_navigation():
    servers = load_servers()

    with ui.header().classes('items-center justify-between'):
        ui.label('TimeKPR').classes('text-lg font-bold')

        with ui.row():
            ui.link('Home', '/')

            if not servers:
                ui.link('Servers', '/servers')
                return

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
                        for user in users:
                            with ui.menu(f'User: {user}'):
                                ui.menu_item(
                                    'Config',
                                    on_click=lambda s=server_name, u=user:
                                    ui.navigate.to(f'/server/{s}/user/{u}')
                                )
                                ui.menu_item(
                                    'Stats',
                                    on_click=lambda s=server_name, u=user:
                                    ui.navigate.to(f'/server/{s}/stats/{u}')
                                )


# -------------------------------------------------------------------
# Route registration
# -------------------------------------------------------------------

def register_routes():
    ui.page('/', home_page)

    servers = load_servers()

    if not servers:
        ui.page('/servers', _no_server_page)
        return

    for server_name in servers:
        ui.page(
            f'/server/{server_name}',
            lambda s=server_name: server_config_page(s)
        )

        for user in list_users(server_name):
            ui.page(
                f'/server/{server_name}/user/{user}',
                lambda s=server_name, u=user: user_config_page(s, u)
            )
            ui.page(
                f'/server/{server_name}/stats/{user}',
                lambda s=server_name, u=user: stats_page(s, u)
            )
