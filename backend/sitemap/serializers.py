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
    worker_count = serializers.SerializerMethodField()
    current_occupancy = serializers.SerializerMethodField()

    class Meta(ZoneSerializer.Meta):
        fields = ZoneSerializer.Meta.fields + ("worker_count", "current_occupancy")

    def get_worker_count(self, obj):
        workers = getattr(obj, "workers", None)
        if workers is not None:
            return workers.count()
        return obj.workers.count()

    def get_current_occupancy(self, obj):
        workers = getattr(obj, "workers", None)
        if workers is not None:
            return workers.filter(is_active=True).count()
        return obj.workers.filter(is_active=True).count()
