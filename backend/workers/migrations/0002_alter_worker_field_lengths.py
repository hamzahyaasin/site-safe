from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workers", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="worker",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="worker",
            name="vest_id",
            field=models.CharField(db_index=True, max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name="worker",
            name="zone",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
