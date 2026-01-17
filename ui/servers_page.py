from nicegui import ui
from servers import load_servers, save_servers
from state import current_server

@ui.page('/servers')
def servers_page():
    ui.label('Servers').classes('text-2xl font-bold')
    servers = load_servers()

    for name, srv in servers.items():
        with ui.card():
            ui.label(name).classes('text-xl')
            ui.button('Select', on_click=lambda n=name: (
                setattr(__import__('state'), 'current_server', n),
                ui.open('/')
            ))

            ui.label('Users:')
            for user in srv.get('users', {}):
                with ui.row():
                    ui.label(user)
                    ui.button(
                        'Delete',
                        on_click=lambda u=user, s=srv: (
                            s['users'].pop(u),
                            save_servers(servers),
                            ui.notify('User deleted')
                        )
                    )

            username = ui.input('New user')
            config = ui.input('Config path')
            stats = ui.input('Stats path')

            def add():
                srv.setdefault('users', {})[username.value] = {
                    'config': config.value,
                    'stats': stats.value,
                }
                save_servers(servers)
                ui.notify('User added')

            ui.button('Add user', on_click=add)
