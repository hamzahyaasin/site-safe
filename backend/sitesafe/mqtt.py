import json

import paho.mqtt.client as mqtt
from django.conf import settings

MQTT_BROKER = settings.MQTT_BROKER_HOST
MQTT_PORT = settings.MQTT_PORT


def on_connect(client, userdata, flags, rc):
    client.subscribe("sitesafe/vest/+/telemetry")
    client.subscribe("sitesafe/vest/+/sos")


def on_message(client, userdata, msg):
    """Route incoming MQTT messages to the appropriate handler."""
    import django

    django.setup()

    from workers.mqtt_handlers import handle_sos, handle_telemetry

    topic_parts = msg.topic.split("/")
    vest_id = topic_parts[2]
    msg_type = topic_parts[3]
    payload = json.loads(msg.payload.decode())

    if msg_type == "telemetry":
        handle_telemetry(vest_id, payload)
    elif msg_type == "sos":
        handle_sos(vest_id, payload)


def start_mqtt_listener():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client
