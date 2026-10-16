from django.db import models


class Worker(models.Model):
    """A site worker. Their vest, if any, is ``smart_vest`` (SmartVest.worker),
    the single source of truth for which vest a worker wears; ``zone`` is the
    zone they are assigned to work in, not where they currently are."""

    name = models.CharField(max_length=100)
    zone = models.ForeignKey(
        "sitemap.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workers",
    )
    role = models.CharField(max_length=50, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def vest_id(self):
        vest = getattr(self, "smart_vest", None)
        return vest.vest_id if vest else None


class SmartVest(models.Model):
    vest_id = models.CharField(max_length=50, unique=True, db_index=True)
    worker = models.OneToOneField(
        "Worker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="smart_vest",
    )
    firmware_version = models.CharField(max_length=20, blank=True, default="")
    battery_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="0-100 percent as last reported; null until the vest reports it",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    sos_active = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered_at"]

    def __str__(self):
        return self.vest_id


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        CHECK_IN = "CHECK_IN", "Check In"
        CHECK_OUT = "CHECK_OUT", "Check Out"
        IDLE_START = "IDLE_START", "Idle Start"
        IDLE_END = "IDLE_END", "Idle End"
        ZONE_ENTER = "ZONE_ENTER", "Zone Enter"
        ZONE_EXIT = "ZONE_EXIT", "Zone Exit"

    worker = models.ForeignKey(
        "Worker",
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    zone = models.ForeignKey(
        "sitemap.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.worker} — {self.action} @ {self.timestamp}"
