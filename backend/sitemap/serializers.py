from rest_framework import serializers

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
