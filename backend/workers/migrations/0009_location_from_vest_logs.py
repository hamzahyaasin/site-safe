"""Fill each worker's last known location from their latest vest zone log.

Before 0008 only vest GPS placed workers, through ZONE_ENTER/ZONE_EXIT logs.
Workers whose latest zone log is an entry keep that zone as their location,
dated to the log and attributed to their vest, so the change does not empty
zone head counts until the next GPS report.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Worker = apps.get_model("workers", "Worker")
    ActivityLog = apps.get_model("workers", "ActivityLog")
    SmartVest = apps.get_model("workers", "SmartVest")
    for worker in Worker.objects.filter(location_at__isnull=True):
        last = (
            ActivityLog.objects.filter(worker=worker, action__in=["ZONE_ENTER", "ZONE_EXIT"])
            .order_by("-timestamp", "-id")
            .first()
        )
        if last is None or last.action != "ZONE_ENTER" or last.zone_id is None:
            continue
        vest = SmartVest.objects.filter(worker=worker).first()
        worker.location_zone_id = last.zone_id
        worker.location_at = last.timestamp
        worker.location_source = "vest"
        worker.location_device = vest.vest_id if vest else ""
        worker.save(update_fields=["location_zone", "location_at", "location_source", "location_device"])


class Migration(migrations.Migration):
    dependencies = [("workers", "0008_camera_location")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
