from django.db import migrations

# Default global rules so the Settings page starts with one editable row per
# alert type. Inactivity uses threshold_seconds as its stationary timeout.
DEFAULTS = {
    "PPE_VIOLATION": 300,
    "SOS": 0,
    "ZONE_BREACH": 0,
    "INACTIVITY": 300,
    "VEHICLE_PROXIMITY": 0,
    "FALL": 0,
}


def seed(apps, schema_editor):
    AlertConfig = apps.get_model("alerts", "AlertConfig")
    for alert_type, threshold in DEFAULTS.items():
        AlertConfig.objects.get_or_create(
            zone=None,
            alert_type=alert_type,
            defaults={
                "is_enabled": True,
                "threshold_seconds": threshold,
                "notify_push": True,
                "notify_email": alert_type in ("SOS", "FALL"),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("alerts", "0008_alert_confidence_alert_event_id_and_more")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
