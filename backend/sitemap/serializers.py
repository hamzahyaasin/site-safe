from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from sitesafe.validation import validate_camera_ids, validate_polygon

from .models import CameraArea, HotWorkPermit, Zone


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


class CameraAreaSerializer(serializers.ModelSerializer):
    MAX_VERTICES = 24

    class Meta:
        model = CameraArea
        fields = ("id", "camera_id", "name", "polygon", "severity", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
        validators = []  # the per-camera name check below gives a readable message

    def validate_camera_id(self, value):
        from alerts.live import CAMERA_ID

        value = value.strip()
        if not CAMERA_ID.match(value):
            raise serializers.ValidationError("Use letters, digits, '.', '_' or '-' (up to 64).")
        return value

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_polygon(self, value):
        if not isinstance(value, list) or not 3 <= len(value) <= self.MAX_VERTICES:
            raise serializers.ValidationError(f"An area needs 3 to {self.MAX_VERTICES} points.")
        points = []
        for point in value:
            if not (isinstance(point, (list, tuple)) and len(point) == 2):
                raise serializers.ValidationError("Each point must be [x, y].")
            try:
                x, y = float(point[0]), float(point[1])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("Each point must be [x, y] numbers.") from exc
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise serializers.ValidationError("Points are fractions of the image size, from 0 to 1.")
            points.append([round(x, 4), round(y, 4)])
        if len({tuple(p) for p in points}) < 3:
            raise serializers.ValidationError("An area needs at least three distinct points.")
        return points

    def validate(self, attrs):
        camera_id = attrs.get("camera_id", getattr(self.instance, "camera_id", None))
        name = attrs.get("name", getattr(self.instance, "name", None))
        clash = CameraArea.objects.filter(camera_id=camera_id, name__iexact=name)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"name": f"{camera_id} already has an area called {name}."})
        return attrs
