from django.db import models


class AlertType(models.TextChoices):
    PPE_VIOLATION = "PPE_VIOLATION", "PPE violation"
    FALL = "FALL", "Fall"
    GAS_LEAK = "GAS_LEAK", "Gas leak"
    HEAT_STRESS = "HEAT_STRESS", "Heat stress"
    SOS = "SOS", "SOS"
    INTRUSION = "INTRUSION", "Intrusion"


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class AlertSource(models.TextChoices):
    AI_CAMERA = "AI_CAMERA", "AI Camera"
    IOT_VEST = "IOT_VEST", "IoT Vest"
    SIMULATED = "SIMULATED", "Simulated"


class Alert(models.Model):
    worker = models.ForeignKey(
        "workers.Worker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    alert_type = models.CharField(
        max_length=32,
        choices=AlertType.choices,
    )
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
    )
    source = models.CharField(
        max_length=32,
        choices=AlertSource.choices,
        default=AlertSource.AI_CAMERA,
    )
    description = models.TextField(blank=True, default="")
    is_resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        vid = self.worker.vest_id if self.worker_id else "—"
        return f"{self.alert_type} — {vid} @ {self.timestamp}"
