from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User

from .models import Alert


@receiver(post_save, sender=Alert)
def alert_push_notification(sender, instance, created, **kwargs):
    if not created:
        return

    from sitesafe.notifications import send_push_notification

    user_ids = list(User.objects.filter(is_active=True).values_list("id", flat=True))
    title = f"Site-Safe: {instance.get_alert_type_display()}"
    body = instance.description or instance.get_severity_display()
    data = {
        "alert_id": str(instance.id),
        "alert_type": instance.alert_type,
        "severity": instance.severity,
    }
    send_push_notification(user_ids, title, body, data)
