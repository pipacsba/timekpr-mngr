from nicegui import ui
from servers import load_servers
from state import current_server

def navigation():
    ui.link('Dashboard', '/')
    ui.link('Servers', '/servers')

    if not current_server:
        return

    servers = load_servers()
    srv = servers[current_server]

    ui.link('Server Config', '/config/server')

    with ui.dropdown('Users'):
        for u in srv.get('users', {}):
            ui.link(u, f'/config/user/{u}')

    with ui.dropdown('Stats'):
        for u in srv.get('users', {}):
            ui.link(u, f'/stats/{u}')
