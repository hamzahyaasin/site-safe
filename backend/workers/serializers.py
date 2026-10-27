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
    # Computed from last_seen, so a vest that silently stopped reporting is
    # never shown as online even before the presence sweep has run.
    is_online = serializers.SerializerMethodField()

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
        # Telemetry fields are written only by the vest itself (gateway/MQTT),
        # never typed in through the registry.
        read_only_fields = (
            "id",
            "worker_name",
            "battery_level",
            "latitude",
            "longitude",
            "sos_active",
            "last_seen",
            "registered_at",
        )

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None

    def validate_worker(self, worker):
        if worker is None:
            return worker
        if not worker.is_active:
            raise serializers.ValidationError("Cannot assign a vest to a deactivated worker.")
        current = getattr(worker, "smart_vest", None)
        if current is not None and (self.instance is None or current.pk != self.instance.pk):
            raise serializers.ValidationError(
                f"{worker.name} already wears vest {current.vest_id}; unassign it first."
            )
        return worker

    def get_is_online(self, obj):
        from .presence import is_vest_online

        return is_vest_online(obj)


class WorkerSerializer(serializers.ModelSerializer):
    """Worker with their vest. Assign a vest by writing its id to ``vest``
    (null to unassign); ``vest_id`` and ``smart_vest`` are read-only views."""

    zone_name = serializers.SerializerMethodField()
    smart_vest = SmartVestSerializer(read_only=True)
    vest_id = serializers.SerializerMethodField()
    # Where the worker is: the zone a camera badge sighting or vest GPS last
    # placed them in, and whether that is still current (see workers.location).
    location = serializers.SerializerMethodField()
    vest = serializers.PrimaryKeyRelatedField(
        queryset=SmartVest.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Worker
        fields = (
            "id",
            "name",
            "vest_id",
            "vest",
            "zone",
            "zone_name",
            "role",
            "phone",
            "smart_vest",
            "location",
            "last_seen_at",
            "last_seen_source",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "zone_name", "smart_vest", "location", "last_seen_at", "last_seen_source", "created_at")

    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone_id else None

    def get_vest_id(self, obj):
        return obj.vest_id

    def get_location(self, obj):
        from .location import is_current

        if obj.location_at is None:
            return None
        return {
            "zone": obj.location_zone_id,
            "zone_name": obj.location_zone.name if obj.location_zone_id else None,
            "source": obj.location_source,
            "device": obj.location_device,
            # Formatted here: broadcast payloads are encoded with plain json.dumps.
            "at": serializers.DateTimeField().to_representation(obj.location_at),
            "current": is_current(obj),
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_vest(self, vest):
        if vest is None:
            return vest
        if vest.worker_id and (self.instance is None or vest.worker_id != self.instance.pk):
            raise serializers.ValidationError(
                f"Vest {vest.vest_id} is already assigned to {vest.worker.name}."
            )
        return vest

    def _assign_vest(self, worker, vest):
        from django.db import transaction

        with transaction.atomic():
            for old in SmartVest.objects.filter(worker=worker).exclude(pk=getattr(vest, "pk", None)):
                old.worker = None
                old.save(update_fields=["worker"])
            if vest is not None and vest.worker_id != worker.pk:
                vest.worker = worker
                vest.save(update_fields=["worker"])
        # Drop the cached reverse relation so the response shows the new vest.
        worker._state.fields_cache.pop("smart_vest", None)

    def create(self, validated_data):
        assign = "vest" in validated_data
        vest = validated_data.pop("vest", None)
        worker = super().create(validated_data)
        if assign:
            self._assign_vest(worker, vest)
        return worker

    def update(self, instance, validated_data):
        assign = "vest" in validated_data
        vest = validated_data.pop("vest", None)
        worker = super().update(instance, validated_data)
        if assign:
            self._assign_vest(worker, vest)
        # A deactivated worker no longer wears a vest.
        if not worker.is_active:
            self._assign_vest(worker, None)
        return worker


class VestTelemetrySerializer(serializers.Serializer):
    """Validated vest telemetry, shared by the HTTP gateway endpoint and MQTT."""

    vest_id = serializers.CharField(max_length=50, required=False)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    battery_level = serializers.IntegerField(required=False, min_value=0, max_value=100)
    sos_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        from sitesafe.validation import validate_lat_lng

        has_lat = attrs.get("latitude") is not None
        has_lng = attrs.get("longitude") is not None
        if has_lat != has_lng:
            raise serializers.ValidationError("latitude and longitude must be sent together.")
        if has_lat:
            attrs["latitude"], attrs["longitude"] = validate_lat_lng(
                attrs["latitude"], attrs["longitude"]
            )
        else:
            attrs.pop("latitude", None)
            attrs.pop("longitude", None)
        return attrs
