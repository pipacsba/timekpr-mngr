# ui/navigation.py
from nicegui import app, ui
from fastapi import Request
from servers import load_servers, list_users
from ssh_sync import change_upload_is_pending, trigger_ssh_sync
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard
from storage import DATA_ROOT, get_admin_user_list

import os
import pty
import signal
from functools import partial
from nicegui import core, events

import logging
logger = logging.getLogger(__name__)

# -------------------
# Refreshable items
# -------------------

@ui.refreshable
def pending_ui():
        a_color = 'green'
        if change_upload_is_pending.get_value():
          a_color = 'red'
          b_color = 'bg-red'
          b_text = 'Upload is pending'
        else:
          a_color = 'green'
          b_color = 'bg-green'
          b_text = 'No upload is pending'
        with ui.icon('circle', color=f'{a_color}').classes('text-5xl'):
                ui.tooltip(f'{b_text}').classes(f'{b_color}')

def pending_ui_refresh():
  pending_ui.refresh()
        
change_upload_is_pending.add_observer(pending_ui_refresh)
##  RuntimeError: Request is not set
#client = ui.context.client
#client.on_disconnect(lambda: change_upload_is_pending.remove_observer(pending_ui_refresh))

def refresh_ssh_sync():
    ui.notify("SSH syncronziation is triggered")
    trigger_ssh_sync()

def get_ha_user(request: Request):
    # HA passes the username and user ID via headers
    username = request.headers.get("x-remote-user-name")
    user_id = request.headers.get("x-remote-user-id")
    return username, user_id

# -------------------
# Header (called inside each page)
# -------------------
def build_header():
    dark = ui.dark_mode()
    dark.enable()
    with ui.header().classes('items-center'):
        ui.colors(brand='#424242')
        ui.label('TimeKPR Manager').classes('text-lg font-bold text-brand')
        ui.link('Servers', '/servers').classes('font-bold text-brand')
        ui.link('pty', '/pty').classes('font-bold text-brand')
        ui.link('browse_folders', '/browse_folders').classes('font-bold text-brand')
        ui.space()
        ui.label(f"{app.storage.client.get('ha_username', False)}").classes('font-bold text-brand')
        with ui.icon('refresh', color=f'green').on('click', refresh_ssh_sync).classes('text-5xl cursor-pointer'):
             ui.tooltip(f'Reload server info').classes(f'green')
        pending_ui()

# -------------------
# Pages
# -------------------
@ui.page('/')
def home_page(request: Request):
    ha_user = request.headers.get("x-remote-user-name", "unknown")
    if app.storage.client.get('ha_username', "") != "":
            app.storage.general['admin_users'] = get_admin_user_list()
    app.storage.client['is_admin'] = (ha_user in app.storage.general.get("admin_list", list))
    app.storage.client['ha_username'] = ha_user
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
    logger.info(f"pty is started")
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
        logger.info(f"pty is closed")

@ui.page('/browse_folders')
def browse_folders():
    logger.info(f"Folder browser is started")
    build_header()
    
    def get_tree_data(path):
        """Recursively builds a list of dicts for ui.tree."""
        nodes = []
        # Sort to show directories first, then files
        items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x))
        
        for name in items:
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            
            node = {'id': full_path, 'label': name}
            if is_dir:
                # Recursively add children for subfolders
                node['children'] = get_tree_data(full_path)
                node['icon'] = 'folder'
            else:
                # Only include text-like files
                if name.endswith(('.conf', '.json', '.stats')):
                    node['icon'] = 'description'
                    nodes.append(node)
                continue # Skip non-text files
                
            nodes.append(node)
        return nodes
    
    def handle_select(e):
        """Event handler for when a node in the tree is clicked."""
        selected_path = e.value
        if selected_path and os.path.isfile(selected_path):
            try:
                with open(selected_path, 'r', encoding='utf-8') as f:
                    content_display.set_content(f'```text\n{f.read()}\n```')
            except Exception as err:
                ui.notify(f'Error: {err}', type='negative')
        elif selected_path and os.path.isdir(selected_path):
            # Optional: update display to indicate a folder was selected
            content_display.set_content('*Select a file to view content*')
    
    # --- UI Layout ---
    with ui.row().classes('w-full h-screen no-wrap'):
        # Sidebar: Directory Tree
        with ui.column().classes('w-1/4 bg-gray-500 p-4 border-r'):
            ui.label('File Explorer').classes('text-lg font-bold mb-2')
            
            tree_nodes = get_tree_data(DATA_ROOT)
            if not tree_nodes:
                ui.label('No files found').classes('italic text-white')
            else:
                # Create the tree with the built nodes
                ui.tree(tree_nodes, label_key='label', on_select=handle_select).classes('w-full')
    
        # Main Area: Content display
        with ui.column().classes('w-3/4 p-4'):
            ui.label('File Content').classes('text-lg font-bold mb-2')
            content_display = ui.markdown('Select a file from the tree to view...') \
                .classes('w-full border p-4 bg-gray-500 min-h-[500px] overflow-auto')
