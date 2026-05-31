from rest_framework import serializers

from .models import ActivityLog, SmartVest, Worker


class ActivityLogSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = (
            "id",
            "worker",
            "worker_name",
            "action",
            "zone",
            "timestamp",
            "metadata",
        )
        read_only_fields = ("id", "worker_name", "timestamp")

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None


class SmartVestSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()

    class Meta:
        model = SmartVest
        fields = (
            "id",
            "vest_id",
            "worker",
            "worker_name",
            "firmware_version",
            "battery_level",
            "latitude",
            "longitude",
            "sos_active",
            "is_online",
            "last_seen",
            "registered_at",
        )
        read_only_fields = ("id", "worker_name", "registered_at")

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None


class WorkerSerializer(serializers.ModelSerializer):
    zone_name = serializers.SerializerMethodField()
    smart_vest = SmartVestSerializer(read_only=True)

    class Meta:
        model = Worker
        fields = (
            "id",
            "name",
            "vest_id",
            "zone",
            "zone_name",
            "role",
            "phone",
            "smart_vest",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "zone_name", "smart_vest", "created_at")

    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone_id else None
