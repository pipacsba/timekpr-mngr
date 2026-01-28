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


def publish(topic: str, payload: dict, *, qos: int = 1, retain: bool = False) -> None:
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
    unique_id: str,
    name: str,
    state_topic: str,
    value_template: str,
    unit: str = "s",
    device: dict,
):
    payload = {
        "name": name,
        "state_topic": f"{MQTT_BASE}/{state_topic}",
        "value_template": value_template,
        "unit_of_measurement": unit,
        "state_class": "measurement",
        "device_class": "duration",
        "unique_id": unique_id,
        "device": device,
    }

    publish(
        topic=,
        payload=payload,
        qos=1,
        retain=True,
    )

    try:
        client = get_client()
        client.publish(
            f"homeassistant/sensor/{unique_id}/config",
            json.dumps(payload),
            qos=1,
            retain=True,
        )
    except Exception as e:
        logger.warning(f"MQTT publish discovery data failed: {e}")
