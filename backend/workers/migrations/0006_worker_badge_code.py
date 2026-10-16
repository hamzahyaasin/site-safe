import secrets

from django.db import migrations, models

import workers.models


def fill_badge_codes(apps, schema_editor):
    Worker = apps.get_model("workers", "Worker")
    for worker in Worker.objects.filter(badge_code__isnull=True):
        worker.badge_code = secrets.token_urlsafe(9)
        worker.save(update_fields=["badge_code"])


class Migration(migrations.Migration):
    dependencies = [("workers", "0005_vest_battery_unknown")]

    operations = [
        # Add nullable first, give each existing worker its own random code,
        # then make it unique and required.
        migrations.AddField(
            model_name="worker",
            name="badge_code",
            field=models.CharField(max_length=32, null=True),
        ),
        migrations.RunPython(fill_badge_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="worker",
            name="badge_code",
            field=models.CharField(
                default=workers.models.new_badge_code,
                help_text="Random identifier encoded in the worker's QR badge",
                max_length=32,
                unique=True,
            ),
        ),
    ]
