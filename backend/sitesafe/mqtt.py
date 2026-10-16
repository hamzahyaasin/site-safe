"""MQTT consumer for vest telemetry and SOS messages.

Run it as its own process with ``python manage.py run_mqtt_consumer``. When
it runs separately from the ASGI server, set REDIS_URL so its broadcasts
reach dashboard websocket clients.
"""

import json
import logging

import paho.mqtt.client as mqtt
from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)

TOPICS = ("sitesafe/vest/+/telemetry", "sitesafe/vest/+/sos")


def on_connect(client, userdata, flags, rc):
    if rc != 0:
        logger.error("MQTT connection refused (rc=%s)", rc)
        return
    for topic in TOPICS:
        client.subscribe(topic, qos=1)
    logger.info("MQTT connected; subscribed to %s", ", ".join(TOPICS))


def on_message(client, userdata, msg):
    """Route incoming MQTT messages to the appropriate handler."""
    from workers.mqtt_handlers import handle_sos, handle_telemetry

    parts = msg.topic.split("/")
    if len(parts) != 4 or not parts[2]:
        logger.warning("Ignoring message on unexpected topic %s", msg.topic)
        return
    vest_id, msg_type = parts[2], parts[3]
    try:
        payload = json.loads(msg.payload.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Ignoring non-JSON payload on %s", msg.topic)
        return

    close_old_connections()
    try:
        if msg_type == "telemetry":
            handle_telemetry(vest_id, payload)
        elif msg_type == "sos":
            handle_sos(vest_id, payload)
    except Exception:  # noqa: BLE001 - one bad message must not stop the consumer
        logger.exception("Failed to handle %s", msg.topic)


def build_client():
    client = mqtt.Client(client_id=getattr(settings, "MQTT_CLIENT_ID", "sitesafe-backend"))
    if settings.MQTT_USERNAME:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


def start_mqtt_listener():
    """Start the consumer on a background thread (for embedding)."""
    client = build_client()
    client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_PORT, 60)
    client.loop_start()
    return client
