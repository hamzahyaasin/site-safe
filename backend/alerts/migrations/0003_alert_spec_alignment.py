import django.db.models.deletion
from django.db import migrations, models


def forwards_map_legacy_alert_types(apps, schema_editor):
    Alert = apps.get_model("alerts", "Alert")
    Alert.objects.filter(alert_type="GAS").update(alert_type="GAS_LEAK")
    Alert.objects.filter(alert_type="HEAT").update(alert_type="HEAT_STRESS")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0002_alert_source_extended_choices"),
    ]

    operations = [
        migrations.RunPython(forwards_map_legacy_alert_types, noop_reverse),
        migrations.AddField(
            model_name="alert",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="alert",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="alert",
            name="worker",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alerts",
                to="workers.worker",
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="alert_type",
            field=models.CharField(
                choices=[
                    ("PPE_VIOLATION", "PPE violation"),
                    ("FALL", "Fall"),
                    ("GAS_LEAK", "Gas leak"),
                    ("HEAT_STRESS", "Heat stress"),
                    ("SOS", "SOS"),
                    ("INTRUSION", "Intrusion"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="timestamp",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
