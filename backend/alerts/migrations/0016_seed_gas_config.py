from django.db import migrations


def seed(apps, schema_editor):
    AlertConfig = apps.get_model("alerts", "AlertConfig")
    AlertConfig.objects.get_or_create(
        zone=None,
        alert_type="GAS",
        defaults={"is_enabled": True, "threshold_seconds": 0, "notify_push": True, "notify_email": True},
    )


class Migration(migrations.Migration):
    dependencies = [("alerts", "0015_gas_sensor")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
