import secrets

from django.db import models
from django.utils import timezone

# Printed on worker QR badges as "SSW1:<code>". The code is random and
# carries no personal data; reissuing a badge replaces it, which revokes
# the old printout.
BADGE_PREFIX = "SSW1:"


def new_badge_code():
    return secrets.token_urlsafe(9)


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
    badge_code = models.CharField(
        max_length=32,
        unique=True,
        default=new_badge_code,
        help_text="Random identifier encoded in the worker's QR badge",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time a vest report or QR sighting placed this worker on site",
    )
    last_seen_source = models.CharField(max_length=80, blank=True, default="")
    # Last known location: the zone a camera badge sighting or vest GPS last
    # placed the worker in (None: outside every zone, or a camera with no zone).
    location_zone = models.ForeignKey(
        "sitemap.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    location_at = models.DateTimeField(null=True, blank=True)
    location_source = models.CharField(
        max_length=8,
        blank=True,
        default="",
        choices=[("camera", "Camera"), ("vest", "Vest GPS")],
    )
    location_device = models.CharField(max_length=64, blank=True, default="", help_text="Camera id or vest id")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def badge_payload(self):
        return f"{BADGE_PREFIX}{self.badge_code}"

    def reissue_badge(self):
        self.badge_code = new_badge_code()
        self.save(update_fields=["badge_code"])

    @classmethod
    def from_badge(cls, value):
        """Active worker for a badge code or full ``SSW1:`` payload, else None."""
        if not value:
            return None
        code = value[len(BADGE_PREFIX):] if value.startswith(BADGE_PREFIX) else value
        return cls.objects.filter(badge_code=code, is_active=True).first()

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
    # When it happened, not when it was stored: camera events can arrive late
    # through the outbox, and check-outs are dated to the last sighting.
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.worker} — {self.action} @ {self.timestamp}"
