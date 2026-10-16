from django.conf import settings
from django.core.management.base import BaseCommand

from sitesafe.mqtt import build_client


class Command(BaseCommand):
    help = "Consume vest telemetry/SOS from the MQTT broker until interrupted."

    def handle(self, *args, **options):
        client = build_client()
        host, port = settings.MQTT_BROKER_HOST, settings.MQTT_PORT
        self.stdout.write(f"Connecting to MQTT broker {host}:{port} …")
        client.connect(host, port, 60)
        try:
            client.loop_forever(retry_first_connection=True)
        except KeyboardInterrupt:
            client.disconnect()
