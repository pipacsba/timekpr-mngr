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
    with ui.dialog() as dialog, ui.card().classes('w-[500px]'):
        ui.label('Add Server').classes('text-lg font-bold')

        # -----------------------------
        # Basic server fields
        # -----------------------------
        name = ui.input('Server name')
        host = ui.input('Host')
        port = ui.input('Port', value='22')
        user = ui.input('SSH user')
        server_conf = ui.input(
            'Server config path',
            value='/etc/timekpr/timekpr.conf'
        )

        ui.separator()

        # -----------------------------
        # SSH key handling
        # -----------------------------
        ui.label('SSH Key').classes('font-semibold')

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
        )

        # Disable dropdown if no keys exist
        selected_key.disable() if not keys else None

        ui.label('Or upload a new SSH private key').classes('text-sm text-gray-600')

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
        )

        ui.separator()

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

        with ui.row().classes('justify-end gap-2'):
            ui.button('Cancel', on_click=dialog.close)
            ui.button('Create', on_click=save)

    dialog.open()


# -------------------------------------------------------------------
# User creation dialog
# -------------------------------------------------------------------

def _add_user_dialog(server_name: str):
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Add User to {server_name}').classes('text-lg font-bold')

        username = ui.input('Username')
        user_conf = ui.input(
            'User config path',
            value='/var/lib/timekpr/config/timekpr.USER.conf'
        )
        stats_conf = ui.input(
            'Stats path',
            value='/var/lib/timekpr/work/USER.time'
        )

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

        ui.button('Add', on_click=save)
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
                ui.label(server_name).classes('text-lg font-bold')
                ui.space()
                ui.button(
                    icon='delete', color='warning',
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
                        ui.label(username)
                        ui.space()
                        ui.button(
                            icon='delete', color='warning',
                            on_click=lambda s=server_name: (
                                delete_server(s),
                                _refresh()
                            ),
                        ).props('color=negative')
                        
            ui.button(
                'Add user',
                on_click=lambda s=server_name: _add_user_dialog(s),
            ).classes('mb-2')
