from django.db import migrations


def seed(apps, schema_editor):
    AlertConfig = apps.get_model("alerts", "AlertConfig")
    for alert_type in ("FIRE", "SMOKE"):
        AlertConfig.objects.get_or_create(
            zone=None,
            alert_type=alert_type,
            defaults={"is_enabled": True, "threshold_seconds": 0, "notify_push": True, "notify_email": True},
        )


class Migration(migrations.Migration):
    dependencies = [("alerts", "0010_alert_hot_work_permit_alter_alert_alert_type_and_more")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
