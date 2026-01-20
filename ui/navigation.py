# ui/navigation.py
from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard

import logging
logger = logging.getLogger(__name__)

dark = ui.dark_mode()
dark.enable

# -------------------
# Header (called inside each page)
# -------------------
def build_header():
    with ui.header().classes('items-center'):
        ui.label('TimeKPR Manager').classes('text-lg font-bold')
        ui.link('Home', '/')
        ui.link('Servers', '/servers')

# -------------------
# Pages
# -------------------
@ui.page('/')
def home_page():
    logger.info("home_page called")
    build_header()
    servers = load_servers()

    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
    ui.label('Manage server configuration, users, and statistics.')

    if not servers:
        ui.label('No servers configured yet.').classes('text-red-600 mt-4')
        ui.button('Add server', on_click=lambda: ui.navigate.to('/servers'))


@ui.page('/welcome')
def welcome_page():
    logger.info("welcome_page called")
    build_header()
    ui.label('Welcome').classes('text-3xl font-bold mb-4')
    ui.label('Please add your first server.')


@ui.page('/servers')
def servers_page_wrapper():
    logger.info("servers_page called")
    build_header()
    servers_page()


# Dynamically generate server pages
servers = load_servers()
if not servers:
    # fallback if no servers exist
    @ui.page('/server')
    def no_server_page():
        logger.info("no_server_page called")
        build_header()
        ui.label('No servers configured').classes('text-red-600')
        ui.button('Go to Servers', on_click=lambda: ui.navigate.to('/servers'))
else:
    for server in servers:
        # server config page
        def make_server_page(s):
            @ui.page(f'/server/{s}')
            def server_config():
                logger.info(f"server_config_page called for {s}")
                build_header()
                render_config_editor(server_name=s, config_type='server')
        make_server_page(server)

        # per-user pages
        for user in list_users(server):
            def make_user_page(s, u):
                @ui.page(f'/server/{s}/user/{u}')
                def user_config():
                    logger.info(f"user_config_page called for {s}/{u}")
                    build_header()
                    render_config_editor(server_name=s, config_type='user', username=u)

                @ui.page(f'/server/{s}/stats/{u}')
                def user_stats():
                    logger.info(f"stats_page called for {s}/{u}")
                    build_header()
                    render_stats_dashboard(s, u)
            make_user_page(server, user)
