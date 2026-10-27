from django.conf import settings
from django.db import models
from django.utils import timezone


class ZoneQuerySet(models.QuerySet):
    def for_camera(self, camera_id):
        """Zones that list the given camera_id as one of their assigned cameras."""
        if not camera_id:
            return self.none()
        from django.db import connections

        if connections[self.db].features.supports_json_field_contains:
            return self.filter(camera_ids__contains=[camera_id])
        # SQLite (used by the test settings) has no JSON containment lookup.
        ids = [pk for pk, cams in self.values_list("pk", "camera_ids") if camera_id in (cams or [])]
        return self.filter(pk__in=ids)


class Zone(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        RESTRICTED = "RESTRICTED", "Restricted"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    risk_level = models.CharField(
        max_length=16,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
    )
    boundaries = models.JSONField(
        default=list,
        help_text="List of {lat, lng} polygon vertices",
    )
    camera_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Identifiers of cameras assigned to monitor this zone",
    )
    max_occupancy = models.IntegerField(default=0, help_text="0 = unlimited")
    camera_views_overlap = models.BooleanField(
        default=True,
        help_text=(
            "Whether this zone's cameras can see the same people. If they can, the zone's head count is "
            "the largest single-camera count (never double-counts); if not, the counts are added."
        ),
    )
    # Over-capacity state with hysteresis (workers.location.check_capacity):
    # alert once the zone has been over its limit for ZONE_CAPACITY_CONFIRM_SECONDS,
    # re-arm once it has been back within it for ZONE_CAPACITY_CLEAR_SECONDS.
    over_capacity_since = models.DateTimeField(
        null=True, blank=True, help_text="Start of the current over-capacity period"
    )
    capacity_alerted_at = models.DateTimeField(
        null=True, blank=True, help_text="When the current over-capacity period raised its alert"
    )
    within_capacity_since = models.DateTimeField(
        null=True, blank=True, help_text="When an alerted zone came back within its limit"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ZoneQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.risk_level})"


class Camera(models.Model):
    """What each camera last reported about its view. Rows are created on the
    first report; zone assignment stays in Zone.camera_ids."""

    camera_id = models.CharField(max_length=64, unique=True)
    people_count = models.PositiveIntegerField(default=0, help_text="People in view at counted_at")
    counted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.camera_id


class HotWorkPermitQuerySet(models.QuerySet):
    def active_at(self, when=None):
        when = when or timezone.now()
        return self.filter(revoked_at__isnull=True, starts_at__lte=when, ends_at__gt=when)


class HotWorkPermit(models.Model):
    """Authorises welding, cutting or other flame work in one zone for a time window.

    Fire or smoke seen in that zone during the window is still recorded and
    shown, but at reduced severity and linked to the permit; outside a permit
    it is a critical alert. A permit never hides fire.
    """

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="hot_work_permits")
    description = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    objects = HotWorkPermitQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return f"{self.zone.name}: {self.description} ({self.starts_at:%d %b %H:%M}–{self.ends_at:%H:%M})"

    @property
    def is_active(self):
        now = timezone.now()
        return self.revoked_at is None and self.starts_at <= now < self.ends_at
