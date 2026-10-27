from django.db import models


class AlertType(models.TextChoices):
    PPE_VIOLATION = "PPE_VIOLATION", "PPE violation"
    SOS = "SOS", "SOS"
    ZONE_BREACH = "ZONE_BREACH", "Zone breach"
    INACTIVITY = "INACTIVITY", "Inactivity"
    VEHICLE_PROXIMITY = "VEHICLE_PROXIMITY", "Vehicle proximity"
    FALL = "FALL", "Fall"
    FIRE = "FIRE", "Fire"
    SMOKE = "SMOKE", "Smoke"
    DANGER_AREA = "DANGER_AREA", "Danger area"


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class AlertSource(models.TextChoices):
    AI_CAMERA = "AI_CAMERA", "AI Camera"
    SMART_VEST = "SMART_VEST", "Smart Vest"
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
    camera_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Identifier of the camera/edge source that raised this alert, if any",
    )
    location = models.JSONField(
        null=True,
        blank=True,
        help_text="GPS coords: {lat, lng}",
    )
    snapshot = models.ImageField(
        upload_to="alert_snapshots/",
        null=True,
        blank=True,
        help_text="JPEG of the camera frame that confirmed this alert (FR-29)",
    )
    model_version = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Weights that produced this alert: file name and SHA-256 prefix",
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Detector confidence (0-1) for AI camera alerts",
    )
    event_id = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="Producer-assigned idempotency key; a retried event is stored once",
    )
    hot_work_permit = models.ForeignKey(
        "sitemap.HotWorkPermit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="Active hot-work permit covering this fire/smoke alert, if any",
    )
    is_resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        vid = self.worker.vest_id if self.worker_id else "—"
        return f"{self.alert_type} — {vid} @ {self.timestamp}"


class Detection(models.Model):
    camera_id = models.CharField(max_length=50)
    worker = models.ForeignKey(
        "workers.Worker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    class_name = models.CharField(max_length=50, help_text="YOLO class e.g. no-hardhat, hardhat")
    confidence = models.FloatField()
    bbox = models.JSONField(help_text="[x1, y1, x2, y2]")
    frame_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-frame_timestamp"]

    def __str__(self):
        return f"{self.camera_id} — {self.class_name} ({self.confidence:.2f})"


class AlertConfig(models.Model):
    zone = models.ForeignKey(
        "sitemap.Zone",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    alert_type = models.CharField(max_length=32, choices=AlertType.choices)
    is_enabled = models.BooleanField(default=True)
    threshold_seconds = models.IntegerField(
        default=300,
        help_text="For inactivity: seconds before alert",
    )
    notify_email = models.BooleanField(default=True)
    notify_push = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert_type"],
                condition=models.Q(zone__isnull=True),
                name="unique_global_alert_config",
            ),
            models.UniqueConstraint(
                fields=["zone", "alert_type"],
                condition=models.Q(zone__isnull=False),
                name="unique_zone_alert_config",
            ),
        ]

    def __str__(self):
        zone_name = self.zone.name if self.zone_id else "Global"
        return f"{zone_name} — {self.alert_type}"
