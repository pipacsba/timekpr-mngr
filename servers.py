from storage import SERVERS_FILE, load_json, save_json

def load_servers():
    return load_json(SERVERS_FILE, {})

def save_servers(servers):
    save_json(SERVERS_FILE, servers)

def add_user(server, username, config_path, stats_path):
    server['users'][username] = {
        'config': config_path,
        'stats': stats_path,
    }

def delete_user(server, username):
    server['users'].pop(username, None)
