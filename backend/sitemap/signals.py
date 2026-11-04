from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from alerts.events import publish_gas_monitor, publish_gas_monitor_deleted

from .models import GasMonitor


@receiver(post_save, sender=GasMonitor)
def gas_monitor_saved(sender, instance, **kwargs):
    publish_gas_monitor(instance)


@receiver(post_delete, sender=GasMonitor)
def gas_monitor_deleted(sender, instance, **kwargs):
    publish_gas_monitor_deleted(instance.pk)
