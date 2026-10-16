from django.db.models.signals import post_save
from django.dispatch import receiver

from alerts.events import publish_vest, publish_worker

from .models import SmartVest, Worker


@receiver(post_save, sender=SmartVest)
def vest_saved(sender, instance, **kwargs):
    publish_vest(instance)
    if instance.worker_id:
        publish_worker(instance.worker)


@receiver(post_save, sender=Worker)
def worker_saved(sender, instance, **kwargs):
    publish_worker(instance)
