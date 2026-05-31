from django.utils import timezone
from rest_framework import serializers

from workers.models import Worker

from .models import Alert, AlertSource, AlertType, Detection, Severity


class AlertSerializer(serializers.ModelSerializer):
    """Full alert API shape; worker_name and vest_id are read-only computed fields."""

    worker_name = serializers.SerializerMethodField()
    vest_id = serializers.SerializerMethodField()

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
            "location",
            "snapshot",
            "is_resolved",
            "timestamp",
            "resolved_at",
        )
        read_only_fields = ("id", "worker_name", "vest_id", "timestamp", "resolved_at")

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker_id else None

    def get_vest_id(self, obj):
        return obj.worker.vest_id if obj.worker_id else None

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


class AlertIngestSerializer(serializers.Serializer):
    """Payload from the AI / edge module (identifies worker by vest_id)."""

    vest_id = serializers.CharField(max_length=64)
    alert_type = serializers.ChoiceField(choices=AlertType.choices)
    severity = serializers.ChoiceField(choices=Severity.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.JSONField(required=False, allow_null=True)
    is_resolved = serializers.BooleanField(required=False, default=False)

    def validate_location(self, value):
        if value is None:
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError("location must be an object with lat and lng.")
        if "lat" not in value or "lng" not in value:
            raise serializers.ValidationError("location must include lat and lng.")
        return value

    def create(self, validated_data):
        vest_id = validated_data.pop("vest_id")
        description = validated_data.pop("description", "")
        location = validated_data.pop("location", None)
        try:
            worker = Worker.objects.get(vest_id=vest_id, is_active=True)
        except Worker.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"vest_id": "No active worker found with this vest_id."}
            ) from exc
        return Alert.objects.create(
            worker=worker,
            description=description,
            location=location,
            source=AlertSource.SMART_VEST,
            **validated_data,
        )


class AlertSimulateSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()
    alert_type = serializers.ChoiceField(
        choices=[
            (AlertType.PPE_VIOLATION, AlertType.PPE_VIOLATION.label),
            (AlertType.SOS, AlertType.SOS.label),
            (AlertType.ZONE_BREACH, AlertType.ZONE_BREACH.label),
            (AlertType.INACTIVITY, AlertType.INACTIVITY.label),
        ]
    )
    severity = serializers.ChoiceField(choices=Severity.choices)
    source = serializers.ChoiceField(
        choices=AlertSource.choices,
        default=AlertSource.SIMULATED,
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.JSONField(required=False, allow_null=True)

    def validate_location(self, value):
        if value is None:
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError("location must be an object with lat and lng.")
        if "lat" not in value or "lng" not in value:
            raise serializers.ValidationError("location must include lat and lng.")
        return value

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
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise serializers.ValidationError("bbox must be a list of four numbers [x1, y1, x2, y2].")
        return list(value)

    def create(self, validated_data):
        vest_id = validated_data.pop("vest_id", None)
        worker = validated_data.get("worker")
        if vest_id and not worker:
            try:
                validated_data["worker"] = Worker.objects.get(vest_id=vest_id, is_active=True)
            except Worker.DoesNotExist:
                pass
        return super().create(validated_data)
