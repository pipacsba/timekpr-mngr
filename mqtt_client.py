# mqtt_client.py

import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_HOST = "mqtt.lan"
MQTT_PORT = 1883
MQTT_BASE = "timekpr"

_client = None

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


def publish(topic: str, payload: dict) -> None:
    try:
        client = get_client()
        client.publish(
            f"{MQTT_BASE}/{topic}",
            json.dumps(payload),
            qos=0,
            retain=False,
        )
    except Exception as e:
        logger.warning(f"MQTT publish failed: {e}")
