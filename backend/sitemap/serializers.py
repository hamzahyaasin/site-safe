from rest_framework import serializers

from sitesafe.validation import validate_camera_ids, validate_polygon

from .models import Zone


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
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_boundaries(self, value):
        return validate_polygon(value)

    def validate_camera_ids(self, value):
        return validate_camera_ids(value)

    def validate_max_occupancy(self, value):
        if value < 0:
            raise serializers.ValidationError("max_occupancy must be zero (unlimited) or greater.")
        return value


class ZoneDetailSerializer(ZoneSerializer):
    """Adds ``worker_count`` (active workers *assigned* to the zone) and
    ``current_occupancy`` (workers *observed* inside it by an online vest's
    GPS). Camera-only zones have no observed occupancy."""

    worker_count = serializers.SerializerMethodField()
    current_occupancy = serializers.SerializerMethodField()

    class Meta(ZoneSerializer.Meta):
        fields = ZoneSerializer.Meta.fields + ("worker_count", "current_occupancy")

    def get_worker_count(self, obj):
        return sum(1 for w in obj.workers.all() if w.is_active)

    def get_current_occupancy(self, obj):
        observed = self.context.get("observed_zone_ids")
        if observed is None:
            from workers.presence import observed_zone_ids

            observed = observed_zone_ids()
            self.context["observed_zone_ids"] = observed
        return sum(1 for z in observed.values() if z == obj.pk)
