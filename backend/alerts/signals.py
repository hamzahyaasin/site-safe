from django.db.models.signals import post_save
from django.dispatch import receiver

from .events import publish_alert
from .models import Alert


@receiver(post_save, sender=Alert)
def alert_saved(sender, instance, created, **kwargs):
    # Every producer saves through the ORM, so broadcasting here covers API
    # writes, camera ingest, vest SOS, MQTT and admin edits alike.
    publish_alert(instance, created)
    if created:
        from .notify import schedule

        schedule(instance)
