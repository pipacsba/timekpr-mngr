# ssh_sync.py
"""
SSH synchronization engine.

Responsibilities:
- Periodically check server availability
- Download server / user / stats configs
- Upload pending user modifications
- Never block the UI
"""

import os
import time
import socket
import hashlib
import paramiko
from pathlib import Path
from typing import Dict
from datetime import datetime, date

from stats_history import update_daily_usage
from mqtt_client import publish, publish_ha_sensor


from servers import load_servers, get_remote_paths
from storage import (
    KEYS_DIR,
    PENDING_DIR,
    server_cache_dir,
    user_cache_dir,
    stats_cache_dir,
    pending_dir,
    pending_user_dir,
    pending_stats_dir,
)

import threading
trigger_event = threading.Event()

import logging
logger = logging.getLogger(__name__)


# only allow modern ciphers (AES and CHACHA20)
paramiko.Transport._preferred_ciphers = (
    'aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'chacha20-poly1305@openssh.com'
)
paramiko.Transport._preferred_keys = (
    'ssh-ed25519', 'rsa-sha2-512', 'rsa-sha2-256'
)

#internal variables
class Heartbeat:
    def __init__(self, timeout: float = 10.0):
        self._last_seen = 0.0
        self.timeout = timeout

    def beat(self):
        self._last_seen = time.time()

    def is_alive(self) -> bool:
        return (time.time() - self._last_seen) < self.timeout


sync_heartbeat = Heartbeat(timeout=10)



class VariableWatcher:
    def __init__(self):
        self._value = True
        self.observers = []

    def set_value(self, new_value : bool):
        self._value = new_value
        self.notify(new_value)

    def get_value(self):
        return self._value

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify(self, new_value):
        for observer in self.observers:
            observer()

class ServersWatcher:
    def __init__(self):
        self._value: list[str] = []
        self.observers = []

    def set_value(self, new_value):
        self._value = new_value
        self.notify(new_value)

    def get_value(self):
        return self._value

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify(self, new_value):
        for observer in self.observers:
            observer()

    def remove_observer(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def is_online(self, server_name: str) -> bool:
        return server_name in self._value
        
change_upload_is_pending = VariableWatcher()
servers_online = ServersWatcher()
server_user_list = list()
server_list = list()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _tree_has_any_file(directory):
    found = False
    for _, _, files in os.walk(directory):
        if files:
            found = True
    logger.info(f"Finding files in folder: {directory} with result: {found}")
    return found

def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect(server: Dict, servername: str) -> paramiko.SSHClient | None:
    global servers_online
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=server["host"],
            port=server.get("port", 22),
            username=server["user"],
            key_filename=str(KEYS_DIR / server["key"]),
            timeout=5,
        )
        return client

    except (socket.error, paramiko.SSHException, EOFError) as e:
        if servers_online.is_online(servername):
            logger.warning(f"SSH connect failed to {server['host']}: {e}, which is not expected as in the last cycle the server was considered online")
        else:
            logger.debug(f"SSH connect failed to {server['host']}: {e}, but the servers was offline in the last cycle too")
        try:
            client.close()
        except Exception:
            pass
        return None



def _scp_get_if_changed(sftp, remote: str, local: Path) -> bool:
    """
    Download remote file only if changed.
    Returns True if local file was updated.
    """
    try:
        remote_stat = sftp.stat(remote)
    except FileNotFoundError:
        return False

    local.parent.mkdir(parents=True, exist_ok=True)

    if local.exists():
        local_stat = local.stat()

        # Fast path: same size and timestamp
        if (
            local_stat.st_size == remote_stat.st_size
            and int(local_stat.st_mtime) == int(remote_stat.st_mtime)
        ):
            return False

    tmp = local.with_suffix(local.suffix + ".tmp")

    try:
        sftp.get(remote, str(tmp))
    except Exception as e:
        logger.warning(f"Failed to download {remote}: {e}")
        return False

    if local.exists():
        if _file_hash(tmp) == _file_hash(local):
            tmp.unlink()
            return False

    tmp.replace(local)
    os.utime(local, (remote_stat.st_atime, remote_stat.st_mtime))
    return True


def _scp_put(sftp, local: Path, remote: str) -> bool:
    result = False
    try:
        sftp.put(str(local), remote)
        result = True
    except:
        result = False
    return result

def _trigger_user_file_renewal_over_ssh(client, a_username) -> bool:
    result = True
    try:
        logger.info("ssh command to trigger user stats file renew started")

        #This extra command is required to update the server side file to the Today's one
        command = f'timekpra --getuserinfo {a_username}'
        stdin, stdout, stderr = client.exec_command(command)
        if (stdout.channel.recv_exit_status() == 0):
            logger.debug(f"ssh command to trigger user stats file renew returned with 0 exit code")
            result = (result and True)
    except:
        logger.warning("ssh command to trigger user stats file renew execution failed, caught by exception handler")
        result = False
    return result


def _is_file_modified_today(path: Path) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return mtime.date() == date.today()


def _ssh_update_allowance(a_client, local: Path, a_username) -> bool:
    result = True

    try:
        #sftp.put(str(local), remote)
        logger.debug("ssh command execution started")

        #This extra command is required to update the server side file to the Today's one
        command = f'timekpra --getuserinfo {a_username}'
        stdin, stdout, stderr = a_client.exec_command(command)
        if (stdout.channel.recv_exit_status() == 0):
            logger.debug(f"ssh command returned with 0 exit code")
            result = (result and True)
        else:
            logger.warning(f"ssh command '{command}' returned with non-zero exit code")
            result = False
        time.sleep(0.5)

        # Guard: only run if file is from today - extra time is granted (for) today
        if not _is_file_modified_today(local):
            logger.warning(
                f"Skipping allowance update for {a_username}, it is not granted today. (Extra time is only allowed to grant for the day it is provided, if not used, it is lost) "
            )
        else:        
            text = local.read_text()
            logger.debug("ssh command execution started, file is read")
            for raw in text.splitlines():
                command = raw
                logger.debug(f"ssh command identified:  {command}")
                stdin, stdout, stderr = a_client.exec_command(command)
                logger.debug(f"ssh command returned")
                if (stdout.channel.recv_exit_status() == 0):
                    logger.info(f"ssh command returned with 0 exit code")
                    result = (result and True)
                else:
                    logger.warning(f"ssh command returned with non-zero exit code")
                    result = False
    except:
        logger.warning("ssh command execution failed, caught by exception handler")
        result = False
    return result

def register_server_sensors(server: str):
    publish_ha_sensor(
        payload = {
            "name": f"Timekpr Server {server} status",
            "value_template": f"{{{{ 'true' if '{server}' in value_json.servers else 'false'  }}}}",
            "payload_on": "true",
            "payload_off": "false",
            "unique_id": f"timekpr_{server}_online",
            "state_topic": f"servers/online",
            "device_class": "connectivity",
            "qos": 1,
        },
        platform = "binary_sensor",
    )

def register_user_sensors(server: str, user: str):
    publish_ha_sensor(
        payload = {
            "name": f"{server} {user} Time Used Today",
            "state_topic": f"stats/{server}/{user}",
            "value_template": "{{ value_json.time_spent_day }}",
            "unit_of_measurement": "s",
            "state_class": "measurement",
            "device_class": "duration",
            "unique_id": f"timekpr_{server}_{user}_time",
        },
        platform = "sensor",
    )

    publish_ha_sensor(
        payload = {
            "name": f"{server} {user} Playtime Today",
            "state_topic": f"stats/{server}/{user}",
            "value_template": "{{ value_json.playtime_spent_day }}",
            "unit_of_measurement": "s",
            "state_class": "measurement",
            "device_class": "duration",
            "unique_id": f"timekpr_{server}_{user}_playtime",
        },
        platform = "sensor",
    )

def _update_user_history(server: str, user: str, stats_file: Path, updated: bool, client) -> None:
    """
    Extract TIME_SPENT_DAY and PLAYTIME_SPENT_DAY and update rolling history.
    """
    global server_user_list
    if not stats_file.exists():
        logger.warning(f"No stats file found for {server} / {user} to read daily usage")
        return

    values = {}
    for line in stats_file.read_text().splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            values[k.strip()] = v.strip()

    try:
        last_checked = values.get("LAST_CHECKED", "2000-01-01 01:13:08")
        checked_dt = datetime.strptime(last_checked, "%Y-%m-%d %H:%M:%S")
        if checked_dt.date() == date.today():
            time_spent_day = int(values.get("TIME_SPENT_DAY", 0))
            playtime_spent_day = int(values.get("PLAYTIME_SPENT_DAY", 0))
        else:
            time_spent_day = 0
            playtime_spent_day = 0
            #try to update server side file
            _trigger_user_file_renewal_over_ssh(client, user) 
    except ValueError:
        logger.warning(f"ValueError on reading daily usage for {server} / {user}")        
        return
    if updated:
        update_daily_usage(
            server=server,
            user=user,
            time_spent_day=time_spent_day,
            playtime_spent_day=playtime_spent_day,
        )
    
    if not (f"{server}/{user}") in server_user_list:
        register_user_sensors(server, user)
        server_user_list.append(f"{server}/{user}")

    # MQTT publish actual time usage / user
    publish(
        f"stats/{server}/{user}",
        {
            "time_spent_day": time_spent_day,
            "playtime_spent_day": playtime_spent_day,
        },
        qos=1,
        retain=False,
    )

# -------------------------------------------------------------------
# Download logic
# -------------------------------------------------------------------

def sync_from_server(server_name: str, server: Dict) -> bool:
    """
    Pull all known configs from a server.
    Returns True if server was reachable.
    """
    global server_user_list
    client = _connect(server, server_name)

    if not client:
        return False

    try:
        sftp = client.open_sftp()
        paths = get_remote_paths(server_name)

        # --- server config ---
        if "server" in paths:
            updated = _scp_get_if_changed(
                sftp,
                paths["server"],
                server_cache_dir(server_name) / "server.conf",
            )
            if updated:
                logger.debug(f"[{server_name}] server.conf updated")

        # --- user configs ---
        for user, remote_path in paths.get("users", {}).items():
            updated = _scp_get_if_changed(
                sftp,
                remote_path,
                user_cache_dir(server_name) / f"{user}.conf",
            )
            if updated:
                logger.debug(f"[{server_name}] user {user} config updated")

        # --- stats ---
        for user, remote_path in paths.get("stats", {}).items():
            local = stats_cache_dir(server_name) / f'{user}.stats'
            updated = _scp_get_if_changed(
                sftp,
                remote_path,
                local,
            )
            _update_user_history(server_name, user, local, updated, client)
            if updated:
                logger.debug(f"[{server_name}] stats for {user} updated")


        return True

    finally:
        client.close()


# -------------------------------------------------------------------
# Upload logic
# -------------------------------------------------------------------

def upload_pending(server_name: str, server: Dict) -> bool:
    """
    Upload pending changes if server is reachable.
    """
    logger.debug("ssh upload pending started")
    client = _connect(server, server_name)
    success = True
    if not client:
        return False

    try:
        sftp = client.open_sftp()
        paths = get_remote_paths(server_name)

        # --- server config ---
        server_file = pending_dir(server_name) / "server.conf"
        if server_file.exists():
            if _scp_put(sftp, server_file, paths["server"]):
                server_file.unlink()
                logger.debug(f"[{server_name}] uploaded server.conf")
            else:
                success = False

        # --- user configs ---
        for file in pending_user_dir(server_name).glob("*.conf"):
            username = file.stem
            remote = paths.get("users", {}).get(username)
            if remote:
                if _scp_put(sftp, file, remote):
                    file.unlink()
                    logger.debug(f"[{server_name}] uploaded user {username}")
                else:
                    success = False

        # --- stats ---
        logger.debug("ssh upload check for stats file")
        for file in pending_stats_dir(server_name).glob("*.stats"):
            logger.debug(f"ssh upload check for stats file passed: {file}")
            username = file.stem
            logger.debug(f"ssh upload check for stats file fouind for {server_name} {username}")
            if _ssh_update_allowance(client, file, username):
                file.unlink()
                logger.debug(f"[{server_name}] updated allowance for {username}")
            else:
                logger.warning("ssh upload tats file failed")
                success = False
    except:
        success = False

    finally:
        client.close()
        return success


def trigger_ssh_sync():
    logger.debug("Manual SSH sync triggered")
    trigger_event.set()


# -------------------------------------------------------------------
# Periodic runner
# -------------------------------------------------------------------
def run_sync_loop_with_stop(stop_event, interval_seconds: int = 180) -> None:
    global change_upload_is_pending
    global servers_online
    global server_list
    global sync_heartbeat
    logger.debug("SSH sync loop started")
    success = True

    while not stop_event.is_set():
        online_servers = []
        servers = load_servers()

        for name, server in servers.items():
            reachable = upload_pending(name, server)
            if reachable:
                online_servers.append(name)
                sync_from_server(name, server)
            # independently if the server is reachable let's register it in Home Assistant
            if not name in server_list:
                register_server_sensors(name)
                server_list.append(name)
        
        
        servers_online.set_value(online_servers)
        change_upload_is_pending.set_value(_tree_has_any_file(PENDING_DIR))
        sync_heartbeat.beat()
        
        # MQTT publish online server list
        publish(
            "servers/online",
            {
                "servers": servers_online.get_value(),
            },
            qos=1,
            retain=True,
        )
        
        # clear trigger before waiting
        trigger_event.clear()

        # wait until either:
        # - interval expires
        # - trigger_event is set
        # - stop_event is set
        triggered = trigger_event.wait(interval_seconds)
