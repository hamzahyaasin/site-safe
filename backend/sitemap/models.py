from django.db import models


class ZoneQuerySet(models.QuerySet):
    def for_camera(self, camera_id):
        """Zones that list the given camera_id as one of their assigned cameras."""
        if not camera_id:
            return self.none()
        return self.filter(camera_ids__contains=[camera_id])


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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ZoneQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.risk_level})"
