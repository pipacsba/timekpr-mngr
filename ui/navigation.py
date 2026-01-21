# ui/navigation.py
from nicegui import ui
from servers import load_servers, list_users
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard
from storage import DATA_ROOT

import os
import pty
import signal
from functools import partial
from nicegui import core, events

import logging
logger = logging.getLogger(__name__)

# -------------------
# Header (called inside each page)
# -------------------
def build_header():
    dark = ui.dark_mode()
    dark.enable()
    with ui.header().classes('items-center'):
        ui.colors(brand='#424242')
        ui.label('TimeKPR Manager').classes('text-lg font-bold text-brand')
        #ui.link('Home', '/').classes('font-bold text-brand')
        ui.link('Servers', '/servers').classes('font-bold text-brand')
        ui.link('pty', '/pty').classes('font-bold text-brand')
        ui.link('browse_folders', '/browse_folders').classes('font-bold text-brand')


# -------------------
# Pages
# -------------------
@ui.page('/')
def home_page():
    logger.info("home_page called")
    ui.navigate.history.replace('/servers')
    servers_page_wrapper()
    #ui.navigate.to('/servers')
#    dark = ui.dark_mode()
#    dark.enable()
#    build_header()
#    servers = load_servers()

#    ui.label('TimeKPR Configuration Manager').classes('text-3xl font-bold mb-4')
#    ui.label('Manage server configuration, users, and statistics.')

#    if not servers:
#        ui.navigate.to('/servers')


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

@ui.page('/pty')
def pty_page():
    build_header()
    terminal = ui.xterm()

    pty_pid, pty_fd = pty.fork()  # create a new pseudo-terminal (pty) fork of the process
    if pty_pid == pty.CHILD:
        os.execv('/bin/bash', ('bash',))  # child process of the fork gets replaced with "bash"
    print('Terminal opened')

    @partial(core.loop.add_reader, pty_fd)
    def pty_to_terminal():
        try:
            data = os.read(pty_fd, 1024)
        except OSError:
            print('Stopping reading from pty')  # error reading the pty; probably bash was exited
            core.loop.remove_reader(pty_fd)
        else:
            terminal.write(data)

    @terminal.on_data
    def terminal_to_pty(event: events.XtermDataEventArguments):
        try:
            os.write(pty_fd, event.data.encode('utf-8'))
        except OSError:
            pass  # error writing to the pty; probably bash was exited

    @ui.context.client.on_delete
    def kill_bash():
        os.close(pty_fd)
        os.kill(pty_pid, signal.SIGKILL)
        print('Terminal closed')

@ui.page('/browse_folders')
def browse_folders():
    build_header()
    
    def read_file_content(filename: str):
        """Reads content from the selected file and updates the UI."""
        try:
            path = os.path.join(DATA_ROOT, filename)
            with open(path, 'r', encoding='utf-8') as f:
                content_display.set_content(f'```text\n{f.read()}\n```')
        except Exception as e:
            ui.notify(f'Error reading file: {e}', type='negative')
    
    # 2. Build the UI
    with ui.row().classes('w-full h-screen no-wrap'):
        # Sidebar: List of files
        with ui.column().classes('w-1/4 bg-slate-100 p-4'):
            ui.label('Files in /data').classes('text-lg font-bold')
            
            # Get list of files from local folder
            files = [f for f in os.listdir(DATA_ROOT) if os.path.isfile(os.path.join(DATA_ROOT, f))]
            
            if not files:
                ui.label('No files found').classes('italic text-gray-500')
            else:
                for name in files:
                    ui.button(name, on_click=lambda n=name: read_file_content(n)) \
                        .props('flat align=left').classes('w-full')
    
        # Main Area: Content display
        with ui.column().classes('w-3/4 p-4'):
            ui.label('File Content').classes('text-lg font-bold')
            content_display = ui.markdown('Select a file to view its content...') \
                .classes('w-full border p-4 bg-white min-h-[500px]')
