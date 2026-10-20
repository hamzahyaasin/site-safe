import base64
import binascii
import io

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from sitemap.models import Zone
from sitesafe.validation import validate_bbox, validate_location
from workers.models import Worker

from .models import Alert, AlertConfig, AlertSource, AlertType, Detection, Severity


class AlertSerializer(serializers.ModelSerializer):
    """Full alert API shape; worker_name, vest_id, and zone_name are read-only computed fields."""

    worker_name = serializers.SerializerMethodField()
    vest_id = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    # Not the media URL: images of workers are served only through the
    # authenticated /api/alerts/<id>/snapshot/ endpoint.
    snapshot = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = (
            "id",
            "worker",
            "worker_name",
            "vest_id",
            "alert_type",
            "severity",
            "source",
            "description",
            "camera_id",
            "zone_name",
            "location",
            "snapshot",
            "confidence",
            "model_version",
            "event_id",
            "hot_work_permit",
            "is_resolved",
            "timestamp",
            "resolved_at",
        )
        read_only_fields = (
            "id",
            "worker_name",
            "vest_id",
            "zone_name",
            "model_version",
            "event_id",
            "hot_work_permit",
            "timestamp",
            "resolved_at",
        )

    def validate_location(self, value):
        return validate_location(value)

    def validate_confidence(self, value):
        return _validate_confidence(value)

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None

    def get_vest_id(self, obj):
        return obj.worker.vest_id if obj.worker_id else None

    def get_snapshot(self, obj):
        """API path of the evidence image, or None if there is none."""
        return reverse("alert-snapshot", args=[obj.pk]) if obj.snapshot else None

    def get_zone_name(self, obj):
        """Where the alert happened: the camera's zone, else the zone that
        contains its GPS location. Never the worker's assigned zone."""
        if obj.camera_id:
            zone = Zone.objects.for_camera(obj.camera_id).first()
            if zone:
                return zone.name
        loc = obj.location or {}
        if loc.get("lat") is not None and loc.get("lng") is not None:
            from sitemap.geofence import zone_at

            zones = self.context.setdefault("_active_zones", list(Zone.objects.filter(is_active=True)))
            zone = zone_at(zones, loc["lat"], loc["lng"])
            return zone.name if zone else None
        return None

    def create(self, validated_data):
        validated_data.setdefault("source", AlertSource.AI_CAMERA)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        was_resolved = instance.is_resolved
        instance = super().update(instance, validated_data)
        if instance.is_resolved and not was_resolved and instance.resolved_at is None:
            instance.resolved_at = timezone.now()
            instance.save(update_fields=["resolved_at"])
        return instance


def _validate_confidence(value):
    if value is not None and not 0.0 <= value <= 1.0:
        raise serializers.ValidationError("confidence must be between 0 and 1.")
    return value


def decode_snapshot(value):
    """Validate a base64 JPEG from a camera and return its bytes.

    Rejected: invalid base64, more than ALERT_SNAPSHOT_MAX_BYTES once decoded,
    anything Pillow does not read as a JPEG, and images larger than
    ALERT_SNAPSHOT_MAX_SIDE on either side (a decompression-bomb guard).
    """
    from PIL import Image, UnidentifiedImageError

    limit = settings.ALERT_SNAPSHOT_MAX_BYTES
    too_big = f"snapshot must be at most {limit // 1024} KB."
    # Checked before decoding so an oversized string is never expanded.
    if len(value) > (limit + 2) // 3 * 4:
        raise serializers.ValidationError(too_big)
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise serializers.ValidationError("snapshot must be base64-encoded.") from exc
    if not data:
        raise serializers.ValidationError("snapshot is empty.")
    if len(data) > limit:
        raise serializers.ValidationError(too_big)
    try:
        with Image.open(io.BytesIO(data)) as image:
            kind, size = image.format, image.size
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise serializers.ValidationError("snapshot is not a readable image.") from exc
    if kind != "JPEG":
        raise serializers.ValidationError("snapshot must be a JPEG image.")
    if max(size) > settings.ALERT_SNAPSHOT_MAX_SIDE:
        raise serializers.ValidationError(
            f"snapshot must be at most {settings.ALERT_SNAPSHOT_MAX_SIDE} pixels on each side."
        )
    return data


# Alert types a camera can observe. SOS and zone breaches come from vests.
CAMERA_ALERT_TYPES = (
    AlertType.PPE_VIOLATION,
    AlertType.VEHICLE_PROXIMITY,
    AlertType.INACTIVITY,
    AlertType.FALL,
    AlertType.FIRE,
    AlertType.SMOKE,
)


class CameraEventSerializer(serializers.Serializer):
    """Payload from an authenticated camera worker.

    ``event_id`` is generated by the camera when the event is confirmed and
    reused on every retry, so a delivery that succeeded but whose response was
    lost is not stored twice.
    """

    event_id = serializers.UUIDField()
    camera_id = serializers.CharField(max_length=64)
    alert_type = serializers.ChoiceField(choices=[(t.value, t.label) for t in CAMERA_ALERT_TYPES])
    severity = serializers.ChoiceField(choices=Severity.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    confidence = serializers.FloatField(required=False, allow_null=True, default=None)
    # Decoded from a worker's QR badge by the camera, when one was readable
    # on the person the event concerns. Unknown or revoked codes are stored
    # as unidentified, never matched approximately.
    badge_code = serializers.CharField(required=False, allow_blank=True, default="", max_length=64)
    # Alert evidence (FR-29). The snapshot is a base64 JPEG inside this JSON
    # body rather than a multipart upload, so the camera's outbox can replay
    # one self-contained document and idempotency stays a single check.
    model_version = serializers.CharField(required=False, allow_blank=True, default="", max_length=128)
    snapshot = serializers.CharField(required=False, allow_blank=True, default="", trim_whitespace=False)

    def validate_snapshot(self, value):
        return decode_snapshot(value) if value else None

    def validate_camera_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("camera_id is required.")
        token = self.context.get("service_token")
        if token is not None and not token.allows_camera(value):
            raise serializers.ValidationError("This device token may not report for this camera.")
        return value

    def validate_confidence(self, value):
        return _validate_confidence(value)


class AlertIngestSerializer(serializers.Serializer):
    """Payload from the AI / edge module (identifies worker by vest_id)."""

    vest_id = serializers.CharField(max_length=64)
    alert_type = serializers.ChoiceField(choices=AlertType.choices)
    severity = serializers.ChoiceField(choices=Severity.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    camera_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    location = serializers.JSONField(required=False, allow_null=True)
    is_resolved = serializers.BooleanField(required=False, default=False)

    def validate_location(self, value):
        return validate_location(value)

    def create(self, validated_data):
        simulated = validated_data.pop("simulated", False)
        vest_id = validated_data.pop("vest_id")
        description = validated_data.pop("description", "")
        location = validated_data.pop("location", None)
        try:
            worker = Worker.objects.get(smart_vest__vest_id=vest_id, is_active=True)
        except Worker.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"vest_id": "No active worker found with this vest_id."}
            ) from exc
        return Alert.objects.create(
            worker=worker,
            description=description,
            location=location,
            source=AlertSource.SIMULATED if simulated else AlertSource.SMART_VEST,
            **validated_data,
        )


class AlertSimulateSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()
    # Mirrors the AlertType enum directly rather than restating it, so newly
    # added alert types are simulatable without having to update this list.
    alert_type = serializers.ChoiceField(choices=AlertType.choices)
    severity = serializers.ChoiceField(choices=Severity.choices)
    source = serializers.ChoiceField(
        choices=AlertSource.choices,
        default=AlertSource.SIMULATED,
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    camera_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    location = serializers.JSONField(required=False, allow_null=True)

    def validate_location(self, value):
        return validate_location(value)

    def create(self, validated_data):
        wid = validated_data.pop("worker_id")
        description = validated_data.pop("description", "")
        location = validated_data.pop("location", None)
        try:
            worker = Worker.objects.get(pk=wid, is_active=True)
        except Worker.DoesNotExist as exc:
            raise serializers.ValidationError({"worker_id": "Worker not found or inactive."}) from exc
        return Alert.objects.create(
            worker=worker,
            alert_type=validated_data["alert_type"],
            severity=validated_data["severity"],
            source=validated_data.get("source", AlertSource.SIMULATED),
            description=description,
            camera_id=validated_data.get("camera_id", ""),
            location=location,
            is_resolved=False,
        )


class DetectionSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()
    vest_id = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Detection
        fields = (
            "id",
            "camera_id",
            "worker",
            "worker_name",
            "vest_id",
            "class_name",
            "confidence",
            "bbox",
            "frame_timestamp",
            "created_at",
        )
        read_only_fields = ("id", "worker_name", "created_at")

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None

    def validate_bbox(self, value):
        return validate_bbox(value)

    def validate_confidence(self, value):
        return _validate_confidence(value)

    def validate_camera_id(self, value):
        token = self.context.get("service_token")
        if token is not None and not token.allows_camera(value):
            raise serializers.ValidationError("This device token may not report for this camera.")
        return value

    def create(self, validated_data):
        vest_id = validated_data.pop("vest_id", None)
        worker = validated_data.get("worker")
        if vest_id and not worker:
            try:
                validated_data["worker"] = Worker.objects.get(
                    smart_vest__vest_id=vest_id, is_active=True
                )
            except Worker.DoesNotExist:
                pass
        return super().create(validated_data)


class AlertConfigSerializer(serializers.ModelSerializer):
    zone_name = serializers.SerializerMethodField()

    class Meta:
        model = AlertConfig
        fields = (
            "id",
            "zone",
            "zone_name",
            "alert_type",
            "is_enabled",
            "threshold_seconds",
            "notify_email",
            "notify_push",
            "updated_at",
        )
        read_only_fields = ("id", "zone_name", "updated_at")

    def get_zone_name(self, obj):
        if obj.zone_id:
            return obj.zone.name
        return "Global"

    def validate_threshold_seconds(self, value):
        if value < 0:
            raise serializers.ValidationError("threshold_seconds must be zero or greater.")
        return value

    def validate(self, attrs):
        from .rules import ALWAYS_ENABLED

        alert_type = attrs.get("alert_type", getattr(self.instance, "alert_type", None))
        is_enabled = attrs.get("is_enabled", getattr(self.instance, "is_enabled", True))
        if alert_type in ALWAYS_ENABLED and not is_enabled:
            raise serializers.ValidationError(
                {"is_enabled": f"{AlertType(alert_type).label} alerts cannot be disabled."}
            )
        zone = attrs.get("zone", getattr(self.instance, "zone", None))
        clash = AlertConfig.objects.filter(alert_type=alert_type, zone=zone)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"alert_type": "A rule for this alert type and zone already exists."}
            )
        return attrs


class CameraActivitySerializer(serializers.Serializer):
    """Worker activity seen by a camera for an identified (badge-read) person.

    ``occurred_at`` is the camera's time of the observation, because outbox
    delivery can be delayed; it must be within the last 24 hours and not in
    the future (allowing a minute of clock skew).
    """

    KINDS = ("SIGHTING", "IDLE_START", "IDLE_END")

    event_id = serializers.UUIDField()
    camera_id = serializers.CharField(max_length=64)
    badge_code = serializers.CharField(max_length=64)
    kind = serializers.ChoiceField(choices=[(k, k) for k in KINDS])
    occurred_at = serializers.DateTimeField()

    def validate_camera_id(self, value):
        token = self.context.get("service_token")
        if token is not None and not token.allows_camera(value):
            raise serializers.ValidationError("This device token may not report for this camera.")
        return value

    def validate_occurred_at(self, value):
        from datetime import timedelta

        now = timezone.now()
        if value > now + timedelta(minutes=1):
            raise serializers.ValidationError("occurred_at is in the future; check the camera clock.")
        if value < now - timedelta(hours=24):
            raise serializers.ValidationError("occurred_at is more than 24 hours old.")
        return value
