# ui/navigation.py
from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard

import logging
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Header (called inside pages only)
# --------------------------------------------------
def build_header():
    logger.info(f"Header is built")
    with ui.header().classes('items-center'):
        ui.label('TimeKPR Manager').classes('text-lg font-bold')
        ui.link('Home', '/')
        ui.link('Servers', '/servers')

# --------------------------------------------------
# Pages
# --------------------------------------------------
def home_page():
    logger.info(f"home.page called")
    build_header()
    servers = load_servers()

    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
    ui.label('Manage server configuration, users, and statistics.')

    if not servers:
        logger.info(f"home page renders with no-server")
        ui.label('No servers configured yet.').classes('text-red-600 mt-4')
        ui.button('Add server', on_click=lambda: ui.navigate.to('/servers'))

def welcome_page():
    logger.info(f"welcome.page called")
    build_header()
    ui.label('Welcome').classes('text-3xl font-bold mb-4')
    ui.label('Please add your first server.')

def servers_page_wrapper():
    logger.info(f"servers.page called")
    build_header()
    servers_page()

def server_config_page(server_name: str):
    logger.info(f"server_config.page called")
    build_header()
    render_config_editor(server_name=server_name, config_type='server')

def user_config_page(server_name: str, username: str):
    logger.info(f"user-config.page called")
    build_header()
    render_config_editor(
        server_name=server_name,
        config_type='user',
        username=username,
    )

def stats_page(server_name: str, username: str):
    logger.info(f"stats.page called")
    build_header()
    render_stats_dashboard(server_name, username)

def no_server_page():
    logger.info(f"no-server.page called")
    build_header()
    ui.label('No servers configured').classes('text-red-600')
    ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers'))

# --------------------------------------------------
# Route registration (NO redirects, NO logic)
# --------------------------------------------------
def register_routes():
    logger.info(f"Register routes started")
    ui.page('/', on_visit=home_page)
    ui.page('/welcome', on_visit=welcome_page)
    ui.page('/servers', on_visit=servers_page_wrapper)

    servers = load_servers()
    if not servers:
        logger.info(f"Register routes with no servers")
        ui.page('/server', on_visit=no_server_page)
        return

    for server in servers:
        logger.info(f"Register routes with existing servers")
        ui.page(f'/server/{server}', on_visit=lambda s=server: server_config_page(s))

        for user in list_users(server):
            ui.page(
                f'/server/{server}/user/{user}',
                on_visit=lambda s=server, u=user: user_config_page(s, u),
            )
            ui.page(
                f'/server/{server}/stats/{user}',
                on_visit=lambda s=server, u=user: stats_page(s, u),
            )
