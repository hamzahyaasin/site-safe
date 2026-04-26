from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="source",
            field=models.CharField(
                choices=[
                    ("AI_CAMERA", "AI Camera"),
                    ("IOT_VEST", "IoT Vest"),
                    ("SIMULATED", "Simulated"),
                ],
                default="AI_CAMERA",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="alert_type",
            field=models.CharField(
                choices=[
                    ("PPE_VIOLATION", "PPE violation"),
                    ("FALL", "Fall"),
                    ("GAS", "Gas"),
                    ("HEAT", "Heat"),
                    ("GAS_LEAK", "Gas leak"),
                    ("HEAT_STRESS", "Heat stress"),
                    ("SOS", "SOS"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="severity",
            field=models.CharField(
                choices=[
                    ("LOW", "Low"),
                    ("MEDIUM", "Medium"),
                    ("HIGH", "High"),
                    ("CRITICAL", "Critical"),
                ],
                max_length=16,
            ),
        ),
    ]
