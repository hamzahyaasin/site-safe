from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from sitesafe.validation import validate_camera_ids, validate_polygon

from .models import HotWorkPermit, Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = (
            "id",
            "name",
            "description",
            "risk_level",
            "boundaries",
            "camera_ids",
            "max_occupancy",
            "camera_views_overlap",
            "capacity_alerted_at",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "capacity_alerted_at", "created_at")

    def validate_boundaries(self, value):
        return validate_polygon(value)

    def validate_camera_ids(self, value):
        """A camera belongs to one zone: its sightings place workers there."""
        value = validate_camera_ids(value)
        others = Zone.objects.exclude(pk=getattr(self.instance, "pk", None))
        taken = {cam: zone.name for zone in others for cam in zone.camera_ids or [] if cam in value}
        if taken:
            listed = ", ".join(f"{cam} ({name})" for cam, name in sorted(taken.items()))
            raise serializers.ValidationError(f"Already assigned to another zone: {listed}.")
        return value

    def validate_max_occupancy(self, value):
        if value < 0:
            raise serializers.ValidationError("max_occupancy must be zero (unlimited) or greater.")
        return value


class ZoneDetailSerializer(ZoneSerializer):
    """Adds ``worker_count`` (active workers *assigned* to the zone),
    ``current_occupancy`` (the zone's head count now) and ``occupancy`` (how
    that count was worked out: identified workers placed there by a camera
    sighting or vest GPS, and the zone cameras' people counts, combined by
    the largest count if their views overlap, else by sum)."""

    worker_count = serializers.SerializerMethodField()
    current_occupancy = serializers.SerializerMethodField()
    occupancy = serializers.SerializerMethodField()

    class Meta(ZoneSerializer.Meta):
        fields = ZoneSerializer.Meta.fields + ("worker_count", "current_occupancy", "occupancy")

    def get_worker_count(self, obj):
        return sum(1 for w in obj.workers.all() if w.is_active)

    def _occupancy(self, obj):
        from workers import location

        cache = self.context.setdefault("_occupancy", {})
        if obj.pk not in cache:
            if "_present" not in self.context:
                self.context["_present"] = location.current_zone_ids()
                self.context["_cameras"] = location.fresh_cameras()
            cache[obj.pk] = location.zone_occupancy(
                obj, present=self.context["_present"], cameras=self.context["_cameras"]
            )
        return cache[obj.pk]

    def get_current_occupancy(self, obj):
        return self._occupancy(obj)["count"]

    def get_occupancy(self, obj):
        return self._occupancy(obj)


class HotWorkPermitSerializer(serializers.ModelSerializer):
    MAX_DURATION = timedelta(hours=12)

    zone_name = serializers.CharField(source="zone.name", read_only=True)
    issued_by_email = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = HotWorkPermit
        fields = (
            "id",
            "zone",
            "zone_name",
            "description",
            "starts_at",
            "ends_at",
            "is_active",
            "issued_by_email",
            "created_at",
            "revoked_at",
        )
        read_only_fields = ("id", "zone_name", "is_active", "issued_by_email", "created_at", "revoked_at")

    def get_issued_by_email(self, obj):
        return obj.issued_by.email if obj.issued_by_id else None

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Describe the hot work, e.g. 'Welding level 3 beams'.")
        return value

    def validate(self, attrs):
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        zone = attrs.get("zone", getattr(self.instance, "zone", None))
        if ends <= starts:
            raise serializers.ValidationError({"ends_at": "End must be after start."})
        if ends - starts > self.MAX_DURATION:
            raise serializers.ValidationError({"ends_at": "A permit can cover at most 12 hours."})
        if self.instance is None and ends <= timezone.now():
            raise serializers.ValidationError({"ends_at": "This permit would already have expired."})
        if zone is not None and not zone.is_active:
            raise serializers.ValidationError({"zone": "Permits can only be issued for active zones."})
        return attrs
