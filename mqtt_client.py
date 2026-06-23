# mqtt_client.py

import json
import logging
import paho.mqtt.client as mqtt
from storage import ADDON_CONFIG_FILE, load_json

logger = logging.getLogger(__name__)

addon_options=load_json(ADDON_CONFIG_FILE, {})

try:
    MQTT_HOST = addon_options["mqtt"]["server"]
    MQTT_PORT = addon_options["mqtt"]["port"]
    MQTT_BASE = addon_options["mqtt"]["base_topic"]
    MQTT_ENABLED = True
except:
    MQTT_ENABLED = False
    logger.warning("No MQTT config could be read, disabled")

_client = None

def on_message(client, userdata, msg):
    try:
        if msg.topic == "timekpr/command/add_time":
            # Move the import inside the function to avoid the circular loop
            from ui.config_editor import add_user_extra_time
            
            payload = json.loads(msg.payload.decode('utf-8'))
            
            server_name = payload.get("server_name")
            username = payload.get("username")
            time_to_add = int(payload.get("time_to_add_sec", 0))
            playtime_to_add = int(payload.get("playtime_to_add_sec", 0))
            
            if not server_name or not username:
                logger.error("MQTT Add Time failed: Missing server_name or username")
                return
                
            add_user_extra_time(
                server_name=server_name,
                username=username,
                time_to_add_sec=time_to_add,
                playtime_to_add_sec=playtime_to_add
            )
            logger.info(f"MQTT successfully added time for {username} on {server_name}")
            
    except Exception as e:
        logger.error(f"Error processing MQTT command: {str(e)}")

def get_client() -> mqtt.Client:
    global _client
    if _client:
        return _client

    client = mqtt.Client(client_id="timekpr-mngr")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()

    _client = client
    logger.info("MQTT connected")
    return client

def get_device_info() -> dict:
    device = {
        "identifiers": [f"timekpr-mngr"],
        "name": f"timekpr-mngr",
        "manufacturer": "timekpr-mngr",
        "model": "User Monitor",
    }
    return device

# Make sure you subscribe to the topic when the client connects:
def on_connect(client, userdata, flags, rc):
    # Your existing subscriptions...
    client.subscribe("timekpr/command/add_time")

def publish(topic: str, payload: dict, *, qos: int = 1, retain: bool = False) -> None:
    if MQTT_ENABLED:    
        try:
            client = get_client()
            client.publish(
                f"{MQTT_BASE}/{topic}",
                json.dumps(payload),
                qos=qos,
                retain=retain,
            )
        except Exception as e:
            logger.warning(f"MQTT publish failed: {e}")

def publish_ha_sensor(
    *,
    payload: dict,
    platform: str
):
    logger.info(f"HA Discovery message is to be sent for platform {platform}")
    if MQTT_ENABLED:
        payload["state_topic"] = f"{MQTT_BASE}/{payload['state_topic']}"
        payload["device"] = get_device_info()
        
        try:
            client = get_client()
            client.publish(
                f"homeassistant/{platform}/{payload['unique_id']}/config",
                json.dumps(payload),
                qos=1,
                retain=True,
            )
        except Exception as e:
            logger.warning(f"MQTT publish discovery data failed: {e}")
