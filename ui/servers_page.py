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


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _refresh():
    ui.navigate.to('/servers', reload=True)


# -------------------------------------------------------------------
# Server creation dialog
# -------------------------------------------------------------------

def _add_server_dialog():
    with ui.dialog() as dialog, ui.card():
        ui.label('Add Server').classes('text-lg font-bold')

        name = ui.input('Server name')
        host = ui.input('Host')
        port = ui.input('Port', value='22')
        user = ui.input('SSH user')
        server_conf = ui.input(
            'Server config path',
            value='/etc/timekpr/server.conf'
        )

        key_file: Path | None = None

        def upload_key(e):
            nonlocal key_file
            key_file = KEYS_DIR / e.name
            key_file.write_bytes(e.content)

        ui.upload(
            label='Upload SSH private key',
            on_upload=upload_key,
            auto_upload=True,
        )

        def save():
            if not name.value or not host.value or not user.value:
                ui.notify('Missing required fields', type='negative')
                return

            if not key_file:
                ui.notify('SSH key required', type='negative')
                return

            add_server(
                name=name.value,
                host=host.value,
                user=user.value,
                key=key_file.name,
                port=int(port.value),
                server_config=server_conf.value,
            )
            dialog.close()
            _refresh()

        ui.button('Create', on_click=save)
        ui.button('Cancel', on_click=dialog.close)

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
            value='/etc/timekpr/users/username.conf'
        )
        stats_conf = ui.input(
            'Stats path',
            value='/var/lib/timekpr/stats/username.stats'
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
    ui.label('Servers').classes('text-2xl font-bold')

    ui.button('Add server', on_click=_add_server_dialog).classes('mb-4')

    servers = load_servers()

    if not servers:
        ui.label('No servers configured').classes('text-red')
        return

    for server_name, server in servers.items():
        with ui.card().classes('mb-6'):
            with ui.row().classes('items-center justify-between'):
                ui.label(server_name).classes('text-lg font-bold')

                ui.button(
                    'Delete',
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
            ui.button(
                'Add user',
                on_click=lambda s=server_name: _add_user_dialog(s),
            ).classes('mb-2')

            users = server.get('users', {})
            if not users:
                ui.label('No users').classes('text-gray-500')
            else:
                for username in users:
                    with ui.row().classes('items-center justify-between'):
                        ui.label(username)
                        ui.button(
                            'Delete',
                            on_click=lambda s=server_name, u=username: (
                                delete_user(s, u),
                                _refresh()
                            ),
                        ).props('color=negative')
