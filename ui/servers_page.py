# ui/servers_page.py
"""
Server and user management UI.

Responsibilities:
- Create / delete servers
- Upload SSH keys
- Manage users per server
"""

from pathlib import Path
from nicegui import ui

from servers import (
    load_servers,
    add_server,
    delete_server,
    add_user,
    delete_user,
)
from storage import KEYS_DIR
from ui.config_editor import add_user_extra_time

import logging 
logger = logging.getLogger(__name__)
logger.info(f"ui.servers.py is called at all")

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
        ui.label('SSH Key').classes('font-semibold' 'w-full')

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

        def upload_key(e):
            target = KEYS_DIR / e.name
            target.write_bytes(e.content)

            updated_keys = list_keys()
            selected_key.options = updated_keys
            selected_key.value = e.name
            selected_key.enable()

            ui.notify(f'SSH key "{e.name}" uploaded', type='positive')

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
                    'username', username.value
                ),
                stats_path=stats_conf.value.replace(
                    'username', username.value
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
    time_adjustment = 0
    playtime_adjustment
    with ui.dialog().classes('w-lvw') as dialog, ui.card().classes('w-lvw'):
        ui.label(f'Adjust allowed time for {user.capitalize()} on {server}').classes('text-lg font-bold w-full')

        @ui.refreshable
        def adjusted_time_ui(change_minutes: int, reset: Optional[bool] = False):
            global time_adjustment 
            if reset:
                time_adjustment = 0
            else:
                time_adjustment = time_adjustment + change_minutes
            hours, m = divmod(abs(time_adjustment), 60)
            if time_adjustment < 0:
                hours = 0 - hours 
            ui.markdown(f'Change user time by **{hours}h {m} m**.').classes('w-full')
        
        adjusted_time_ui()
        
        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("-15 min", 
                    on_click = adjusted_time_ui(-15),                
                ).props('color=negative')

        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("reset", 
                    on_click = adjusted_time_ui(0, True),                   
                ).props('color=negative')
        
        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("+15 min", 
                    on_click = adjusted_time_ui(15),                
                ).props('color=negative')

        ui.separator()

        @ui.refreshable
        def adjusted_playtime_ui(change_minutes: int, reset: Optional[bool] = False):
            global playtime_adjustment
            if reset:
                playtime_adjustment = 0
            else:
                playtime_adjustment= playtime_adjustment + change_minutes
            hours, m = divmod(abs(playtime_adjustment), 60)
            if playtime_adjustment < 0:
                hours = 0 - hours 
            ui.markdown(f'Change user PLAY time by **{hours}h {m} m**.').classes('w-full')
        
        adjusted_playtime_ui()
        
        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("-15 min", 
                    on_click = adjusted_playtime_ui(-15),                
                ).props('color=negative')

        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("reset", 
                    on_click = adjusted_playtime_ui(0, True),              
                ).props('color=negative')
        
        with ui.row().classes('justify-end gap-2').classes('w-full'):
                ui.chip("+15 min", 
                    on_click = adjusted_playtime_ui(15),                
                ).props('color=negative')

        
        def save():
            add_user_extra_time(
                server_name=server,
                username=user,
                time_to_add=int(time_adjustment*60),
                playtime_to_add=int(playtime_adjustment*60),
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
    ui.label('Servers').classes('text-2xl font-bold')

    ui.button('Add server', on_click=_add_server_dialog).classes('mb-4')

    servers = load_servers()

    if not servers:
        ui.label('No servers configured').classes('text-red')
        return

    for server_name, server in servers.items():
        with ui.card().classes('mb-6'):
            with ui.row().classes('w-full'):
                #ui.label(server_name).classes('text-lg font-bold')
                #ui.link(server_name, f'/server/{server_name}')
                with ui.link(target=f'/server/{server_name}'):
                    ui.label(server_name).classes('text-lg font-bold')
                
                ui.space()
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
                        with ui.link(target=f'/server/{server_name}/user/{username}'):
                                ui.label(username.capitalize())
                        ui.space()
                        ui.chip(icon='iso', color='green',
                            on_click=lambda s=server_name, u=username: _adjust_user_dialog(s, u),
                        )
                        with ui.link(target=f'/server/{server_name}/stats/{username}'):
                                ui.chip(icon='bar_chart')
                        ui.space()
                        ui.chip(icon='delete', color='warning',
                            on_click=lambda  s=server_name, u=username: (
                                delete_user(s, u),
                                _refresh()
                            ),           
                        ).props('color=negative')
                        
            ui.button(
                'Add user',
                on_click=lambda s=server_name: _add_user_dialog(s),
            ).classes('mb-2')
