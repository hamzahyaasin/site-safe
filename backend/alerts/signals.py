from django.db.models.signals import post_save
from django.dispatch import receiver

from .broadcast import broadcast_alert_created
from .models import Alert


@receiver(post_save, sender=Alert)
def alert_created_broadcast(sender, instance, created, **kwargs):
    if created:
        broadcast_alert_created(instance)
