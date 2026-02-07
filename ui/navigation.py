# ui/navigation.py2
import os
from pathlib import Path
from nicegui import app, ui
from fastapi import Request
from servers import load_servers, list_users
from ssh_sync import change_upload_is_pending, trigger_ssh_sync, sync_heartbeat
from ui.servers_page import servers_page
from ui.config_editor import render_config_editor
from ui.stats_dashboard import render_stats_dashboard
from storage import DATA_ROOT, get_admin_user_list, IS_EDGE 
from datetime import datetime

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
    upload_pending = change_upload_is_pending.get_value()
    sync_alive = sync_heartbeat.is_alive()

    if not sync_alive:
        a_color = 'gray'
        b_color = 'bg-gray'
        b_text = 'Sync loop not running'

    elif upload_pending:
        a_color = 'red'
        b_color = 'bg-red'
        b_text = 'Upload is pending'

    else:
        a_color = 'green'
        b_color = 'bg-green'
        b_text = f'Sync running, no upload pending  ({datetime.now().strftime("%H:%M")})'

    with ui.icon('circle', color=a_color).classes('text-5xl'):
        ui.tooltip(b_text).classes(b_color)


def pending_ui_refresh():
  pending_ui.refresh()

change_upload_is_pending.add_observer(pending_ui_refresh)

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
        if IS_EDGE:
            ui.link('Servers', '/servers').classes('font-bold text-brand')
            ui.link('pty', '/pty').classes('font-bold text-brand')
            ui.link('browse_folders', '/browse_folders').classes('font-bold text-brand')
        ui.space()
        ui.label(f"{app.storage.user.get('ha_username', "no user")}").classes('font-bold text-brand')
        with ui.icon('refresh', color=f'green').on('click', refresh_ssh_sync).classes('text-5xl cursor-pointer'):
             ui.tooltip(f'Reload server info').classes(f'green')
        pending_ui()
        ui.timer(30.0, pending_ui.refresh)

# -------------------
# Pages
# -------------------
@ui.page('/')
def home_page(request: Request):
    ha_user = request.headers.get("x-remote-user-name", "unknown")
    #if app.storage.client.get('ha_username', "") != "":
    app.storage.user['admin_users'] = get_admin_user_list()
    app.storage.user['is_admin'] = (ha_user in app.storage.user.get("admin_users", list()))
    app.storage.user['ha_username'] = ha_user
    #ui.navigate.history.replace('/servers')
    servers_page_wrapper()

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

if IS_EDGE :
    @ui.page('/pty')
    def pty_page():
        logger.info(f"pty is started")
        build_header()
        if app.storage.user.get('is_admin', False):
                   
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
        else:
            ui.label("No rights for this page")

    
    TEXT_EXTENSIONS = ('.conf', '.json', '.stats', '.yaml')
    
    @ui.page('/browse_folders')
    def browse_folders():
        logger.info(f"Folder browser is started")
        build_header()
    
        if app.storage.user.get('is_admin', False):
    
            selected_dir: Path = Path(DATA_ROOT)  # default upload target
    
            def get_tree_data(path):
                """Recursively builds a list of dicts for ui.tree, showing ALL files."""
                nodes = []
                try:
                    items = sorted(
                        os.listdir(path),
                        key=lambda x: (not os.path.isdir(os.path.join(path, x)), x),
                    )
                except Exception:
                    return []
            
                for name in items:
                    full_path = os.path.join(path, name)
                    is_dir = os.path.isdir(full_path)
                    node = {'id': full_path, 'label': name}
            
                    if is_dir:
                        node['children'] = get_tree_data(full_path)
                        node['icon'] = 'folder'
                    else:
                        # Assign 'description' icon only to our allowed text files
                        # Others get a generic 'insert_drive_file' icon
                        if name.endswith(TEXT_EXTENSIONS):
                            node['icon'] = 'description'
                        else:
                            node['icon'] = 'insert_drive_file'
                    
                    # We no longer "Skip" files here; everything gets added to the tree
                    nodes.append(node)
                    
                return nodes
    
            def refresh_tree():
                tree_nodes = get_tree_data(DATA_ROOT)
                tree.props(f'nodes={tree_nodes}')
    
            def update_selected_dir_label():
                selected_dir_label.set_text(f'Upload target: {selected_dir}')
    
            def handle_select(e):
                """Event handler for when a node in the tree is clicked."""
                nonlocal selected_dir
            
                selected_path = e.value
                if not selected_path:
                    return
            
                selected_path = Path(selected_path)
            
                if selected_path.is_file():
                    # Update upload target to parent directory regardless of file type
                    selected_dir = selected_path.parent
                    update_selected_dir_label()
            
                    # Check if the file is in our allowed list before reading
                    if selected_path.suffix.lower() in TEXT_EXTENSIONS:
                        try:
                            with open(selected_path, 'r', encoding='utf-8') as f:
                                # Using the file extension for markdown syntax highlighting
                                lang = selected_path.suffix.strip('.')
                                content_display.set_content(f'### {selected_path.name}\n```{lang}\n{f.read()}\n```')
                        except Exception as err:
                            ui.notify(f'Error: {err}', type='negative')
                            content_display.set_content(f'**Failed to read file:** {err}')
                    else:
                        # Friendly message for files that are in the tree but not "viewable"
                        content_display.set_content(
                            f'### {selected_path.name}\n\n'
                            f'> ℹ️ **Note:** Content viewing is restricted for `{selected_path.suffix}` files.'
                        )
            
                elif selected_path.is_dir():
                    selected_dir = selected_path
                    update_selected_dir_label()
                    content_display.set_content('*Select a supported text file to view content*')
    
            async def upload_file(e):
                nonlocal selected_dir
    
                if not selected_dir:
                    selected_dir = Path(DATA_ROOT)
    
                filename = e.file.name
                target = selected_dir / filename
    
                try:
                    content = await e.file.read()  # SmallFileUpload
                    target.write_bytes(content)
                except Exception as err:
                    ui.notify(f'Upload failed: {err}', type='negative')
                    return
    
                ui.notify(f'Uploaded: {filename}', type='positive')
                refresh_tree()
    
            def open_create_folder_dialog():
                with ui.dialog() as dialog, ui.card().classes('w-[520px]'):
                    ui.label('Create folder').classes('text-lg font-bold')
    
                    folder_name = ui.input('Folder name').classes('w-full')
    
                    def create():
                        nonlocal selected_dir
    
                        name = (folder_name.value or '').strip()
                        if not name:
                            ui.notify('Folder name is required', type='negative')
                            return
    
                        # prevent weird path tricks
                        if '/' in name or '\\' in name:
                            ui.notify('Folder name must not contain slashes', type='negative')
                            return
    
                        try:
                            target = selected_dir / name
                            target.mkdir(parents=True, exist_ok=False)
                        except FileExistsError:
                            ui.notify('Folder already exists', type='warning')
                            return
                        except Exception as err:
                            ui.notify(f'Failed to create folder: {err}', type='negative')
                            return
    
                        ui.notify(f'Folder created: {name}', type='positive')
                        refresh_tree()
                        dialog.close()
    
                    with ui.row().classes('justify-end gap-2 w-full'):
                        ui.button('Cancel', on_click=dialog.close)
                        ui.button('Create', on_click=create)
    
                dialog.open()
    
            # --- UI Layout ---
            with ui.row().classes('w-full h-screen no-wrap'):
                # Sidebar: Directory Tree
                with ui.column().classes('w-1/4 bg-gray-500 p-4 border-r'):
                    ui.label('File Explorer').classes('text-lg font-bold mb-2')
    
                    selected_dir_label = ui.label(f'Upload target: {selected_dir}') \
                        .classes('text-sm text-white mb-2')
    
                    ui.button(
                        'Create folder',
                        icon='create_new_folder',
                        on_click=open_create_folder_dialog,
                    ).classes('w-full mb-2')
    
                    ui.upload(
                        label='Upload file to selected folder',
                        auto_upload=True,
                        on_upload=upload_file,
                    ).classes('w-full mb-4')
    
                    tree_nodes = get_tree_data(DATA_ROOT)
                    if not tree_nodes:
                        ui.label('No files found').classes('italic text-white')
                    else:
                        tree = ui.tree(
                            tree_nodes,
                            label_key='label',
                            on_select=handle_select,
                        ).classes('w-full')
    
                # Main Area: Content display
                with ui.column().classes('w-3/4 p-4'):
                    ui.label('File Content').classes('text-lg font-bold mb-2')
                    content_display = ui.markdown('Select a file from the tree to view...') \
                        .classes('w-full border p-4 bg-gray-500 min-h-[500px] overflow-auto')
    
        else:
            ui.label("No rights for this page")
