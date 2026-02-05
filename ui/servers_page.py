# ui/servers_page.py
"""
Server and user management UI.

Responsibilities:
- Create / delete servers
- Upload SSH keys
- Manage users per server
"""

from pathlib import Path
from nicegui import app, ui
import asyncio

from servers import (
    load_servers,
    add_server,
    delete_server,
    add_user,
    delete_user,
)
from storage import KEYS_DIR, create_backup, restore_backup, DATA_ROOT
from ui.config_editor import add_user_extra_time
from ssh_sync import servers_online

import logging 
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _refresh():
    ui.navigate.to('/servers')


# -------------------------------------------------------------------
# Server creation dialog
# -------------------------------------------------------------------

def _add_server_dialog():
    with ui.dialog() as dialog, ui.card().classes('w-lvw'):
        ui.label('Add Server').classes('text-lg font-bold w-full')

        # -----------------------------
        # Basic server fields
        # -----------------------------
        name = ui.input('Server name').classes('w-full')
        host = ui.input('Host').classes('w-full')
        port = ui.input('Port', value='22').classes('w-full')
        user = ui.input('SSH user').classes('w-full')
        server_conf = ui.input(
            'Server config path',
            value='/etc/timekpr/timekpr.conf'
        ).classes('w-full')

        ui.separator()

        # -----------------------------
        # SSH key handling
        # -----------------------------
        ui.label('SSH Key').classes('font-semibold w-full')

        def list_keys() -> list[str]:
            return sorted(
                p.name for p in KEYS_DIR.iterdir()
                if p.is_file()
            )

        keys = list_keys()

        selected_key = ui.select(
            options=keys,
            label='Select existing SSH key',
            value=keys[0] if keys else None,
        ).classes('w-full')

        # Disable dropdown if no keys exist
        selected_key.disable() if not keys else None

        ui.label('Or upload a new SSH private key').classes('text-sm text-gray-200').classes('w-full')

        async def upload_key(e):
            filename = e.file.name
            target = KEYS_DIR / filename
        
            content = await e.file.read()  # <-- this is the key line
            target.write_bytes(content)
            target.chmod(0o600)  # <-- important
        
            updated_keys = list_keys()
            selected_key.options = updated_keys
            selected_key.value = filename
            selected_key.enable()
        
            ui.notify(f'SSH key "{filename}" uploaded', type='positive')

        ui.upload(
            label='Upload SSH private key',
            auto_upload=True,
            on_upload=upload_key,
        ).classes('w-full')

        ui.separator().classes('w-full')

        # -----------------------------
        # Actions
        # -----------------------------
        def save():
            if not name.value or not host.value or not user.value:
                ui.notify('Missing required fields', type='negative')
                return

            if not selected_key.value:
                ui.notify('SSH key is required', type='negative')
                return

            add_server(
                name=name.value,
                host=host.value,
                user=user.value,
                key=selected_key.value,
                port=int(port.value),
                server_config=server_conf.value,
            )

            ui.notify('Server added successfully', type='positive')
            dialog.close()
            _refresh()

        with ui.row().classes('justify-end gap-2').classes('w-full'):
            ui.button('Cancel', on_click=dialog.close)
            ui.button('Create', on_click=save)

    dialog.open()


# -------------------------------------------------------------------
# User creation dialog
# -------------------------------------------------------------------

def _add_user_dialog(server_name: str):
    with ui.dialog().classes('w-lvw') as dialog, ui.card().classes('w-lvw'):
        ui.label(f'Add User to {server_name}').classes('text-lg font-bold w-full')

        username = ui.input('Username').classes('w-full')
        user_conf = ui.input(
            'User config path',
            value='/var/lib/timekpr/config/timekpr.USER.conf'
        ).classes('w-full')
        stats_conf = ui.input(
            'Stats path',
            value='/var/lib/timekpr/work/USER.time'
        ).classes('w-full')

        def save():
            if not username.value:
                ui.notify('Username required', type='negative')
                return

            add_user(
                server_name=server_name,
                username=username.value,
                user_config_path=user_conf.value.replace(
                    'USER', username.value
                ),
                stats_path=stats_conf.value.replace(
                    'USER', username.value
                ),
            )
            dialog.close()
            _refresh()

        with ui.row().classes('justify-end gap-2').classes('w-full'):
            ui.button('Add', on_click=save)
            ui.button('Cancel', on_click=dialog.close)

    dialog.open()

# -------------------------------------------------------------------
# Adjust user time dialog
# -------------------------------------------------------------------

def _adjust_user_dialog(server: str, user: str):
    global time_adjustment_min
    global playtime_adjustment_min
    time_adjustment_min = 0
    playtime_adjustment_min = 0
    with ui.dialog().classes('w-lvw') as dialog, ui.card().classes('w-lvw'):
        ui.label(f'Adjust allowed time for {user.capitalize()} on {server}').classes('text-lg font-bold w-full')

        @ui.refreshable
        def adjusted_time_ui():
            global time_adjustment_min 
            hours, m = divmod(abs(time_adjustment_min), 60)
            if time_adjustment_min < 0 and hours > 0:
                hours = 0 - hours 
            elif time_adjustment_min < 0:
                m = 0 - m
            ui.markdown(f'Change user time by **{hours}h {m} m**.').classes('w-full')

        def _adjust_time(change_minutes: int, reset = False):
            global time_adjustment_min 
            if reset:
                time_adjustment_min = 0
            else:
                time_adjustment_min = time_adjustment_min + change_minutes
            adjusted_time_ui.refresh()
        
        adjusted_time_ui()
        
        with ui.row().classes('w-full'):
                ui.chip("-15 min", 
                    on_click=lambda:(_adjust_time(-15)),
                )

                ui.chip("reset", 
                    on_click=lambda:( _adjust_time(0, True)),
                )
        
                ui.chip("+15 min", 
                    on_click=lambda:( _adjust_time(15)),
                )

        ui.separator()

        @ui.refreshable
        def adjusted_playtime_ui(change_minutes: int, reset = False):
            global playtime_adjustment_min
            hours, m = divmod(abs(playtime_adjustment_min), 60)
            if playtime_adjustment_min < 0 and hours > 0:
                hours = 0 - hours 
            elif playtime_adjustment_min < 0:
                m = 0 - m
            ui.markdown(f'Change user PLAY time by **{hours}h {m} m**.').classes('w-full')

        def _adjust_playtime(change_minutes: int, reset = False):
            global playtime_adjustment_min 
            if reset:
                playtime_adjustment_min = 0
            else:
                playtime_adjustment_min = playtime_adjustment_min + change_minutes
            adjusted_playtime_ui.refresh()
        
        adjusted_playtime_ui(0, True)
        
        with ui.row().classes('w-full'):
                ui.chip("-15 min", 
                    on_click=lambda:(_adjust_playtime(-15)),
                )

                ui.chip("reset", 
                    on_click=lambda:( _adjust_playtime(0, True)),
                )
        
                ui.chip("+15 min", 
                    on_click=lambda:( _adjust_playtime(15)),
                )

        
        def save():
            add_user_extra_time(
                server_name=server,
                username=user,
                time_to_add_sec=int(time_adjustment_min * 60),
                playtime_to_add_sec=int(playtime_adjustment_min * 60),
            )
            dialog.close()
            _refresh()

        with ui.row().classes('justify-end gap-2').classes('w-full'):
            ui.button('Perform', on_click=save)
            ui.button('Cancel', on_click=dialog.close)

    dialog.open()

# -------------------------------------------------------------------
# Main page
# -------------------------------------------------------------------

def servers_page():
    logger.info(f"ui.servers.py servers_page generation is started")

    # Admin Maintenance Section
    if app.storage.user.get('is_admin', False):
        with ui.card().classes('w-full mb-6 bg-blue-50 dark:bg-slate-800 border-dashed border-2 border-blue-200'):
            with ui.row().classes('items-center w-full px-2'):
                ui.icon('settings', color='primary').classes('text-2xl')
                ui.label('Admin Maintenance').classes('text-lg font-bold')
            
            ui.separator()
            
            with ui.row().classes('gap-4 p-2'):
                # Add Server Button (Existing functionality)
                ui.button('Add Server', icon='add', on_click=_add_server_dialog)
                
                # Backup Button (UI Placeholder)
                def handle_backup():
                    try:
                        backup_path = create_backup()
                        ui.download(backup_path)
                        ui.notify('Backup created and download started', type='positive')
                    except Exception as e:
                        logger.error(f"Backup failed: {e}")
                        ui.notify(f'Backup failed: {e}', type='negative')

                ui.button('Backup', icon='cloud_upload', color='secondary', on_click=handle_backup)
                
                # --- Restore Implementation ---
                async def handle_restore(e):
                    # Save the uploaded file temporarily to process it
                    temp_path = DATA_ROOT / 'temp_restore.zip'
                    content = await e.file.read()
                    temp_path.write_bytes(content)

                    # Confirmation Dialog
                    with ui.dialog() as confirm_dialog, ui.card():
                        ui.label('Confirm Restore').classes('text-lg font-bold text-red-600')
                        ui.markdown('**Warning:** This will permanently replace all current servers, SSH keys, and history with the data from this backup. **This cannot be undone.**')
                        
                        with ui.row().classes('justify-end'):
                            ui.button('Cancel', on_click=confirm_dialog.close)
                            def do_restore():
                                if restore_backup(temp_path):
                                    ui.notify('Restore successful. Reloading...', type='positive')
                                    # Refresh the page to load the new servers.json
                                    ui.timer(1.5, lambda: ui.navigate.to('/servers'))
                                else:
                                    ui.notify('Restore failed. Check logs.', type='negative')
                                confirm_dialog.close()
                                temp_path.unlink(missing_ok=True) # Cleanup
                            
                            ui.button('Overwrite Everything', color='negative', on_click=do_restore)

                    confirm_dialog.open()

                ui.upload(
                    label='Restore from Zip',
                    auto_upload=True,
                    on_upload=handle_restore,
                ).classes('w-full mt-4').props('accept=.zip max-files=1')
    
    
    ui.label('Servers').classes('text-2xl font-bold')

    servers = load_servers()
    refreshables = []

    client = ui.context.client
    
    if not servers:
        ui.label('No servers configured').classes('text-red')
        return

    for server_name, server in servers.items():
        with ui.card().classes('mb-6'):
            with ui.row().classes('w-full'):
                #ui.label(server_name).classes('text-lg font-bold')
                #ui.link(server_name, f'/server/{server_name}')
                if app.storage.user.get('is_admin', False): 
                    with ui.link(target=f'/server/{server_name}'):
                        ui.label(server_name).classes('text-lg font-bold')
                else:
                    ui.label(server_name).classes('text-lg font-bold')
                ui.space()
                @ui.refreshable
                def server_status(name=server_name):
                    if servers_online.is_online(name):
                        ui.chip('ONLINE', color='green')
                    else:
                        ui.chip('OFFLINE', color='gray')
                server_status()
                refreshables.append(server_status)
                if app.storage.user.get('is_admin', False): 
                    ui.chip(icon='delete', color='warning',
                        on_click=lambda s=server_name: (
                            delete_server(s),
                            _refresh()
                        ),                
                ).props('color=negative')

            ui.label(f"Host: {server['host']}:{server.get('port', 22)}")
            ui.label(f"User: {server['user']}")
            ui.label(f"Server config: {server['server_config']}")

            ui.separator()

            ui.label('Users').classes('font-semibold')
            users = server.get('users', {})
            if not users:
                ui.label('No users').classes('text-gray-500')
            else:
                for username in users:
                    with ui.row().classes('w-full'):
                        #ui.label(username)
                        if app.storage.user.get('is_admin', False):                        
                            with ui.link(target=f'/server/{server_name}/user/{username}'):
                                    ui.label(username.capitalize())
                        else:
                            ui.label(username.capitalize())
                        ui.space()
                        if app.storage.user.get('is_admin', False):
                            ui.chip(icon='iso', color='green',
                                on_click=lambda s=server_name, u=username: _adjust_user_dialog(s, u),
                            )
                        with ui.link(target=f'/server/{server_name}/stats/{username}'):
                                ui.chip(icon='bar_chart')
                        if app.storage.user.get('is_admin', False):
                            ui.space()
                            ui.chip(icon='delete', color='warning',
                                on_click=lambda  s=server_name, u=username: (
                                    delete_user(s, u),
                                    _refresh()
                                ),           
                        ).props('color=negative')
            if app.storage.user.get('is_admin', False):            
                ui.button(
                    'Add user',
                    on_click=lambda s=server_name: _add_user_dialog(s),
                ).classes('mb-2')

    def on_servers_changed():
        for r in refreshables:
            r.refresh()
    
    # register observer
    servers_online.add_observer(on_servers_changed)
    
    # remove on disconnect
    client.on_disconnect(lambda: servers_online.remove_observer(on_servers_changed))
