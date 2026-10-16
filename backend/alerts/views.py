from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import datetime, time
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from django.db import IntegrityError, transaction

from accounts.permissions import IsViewer, ReadOnlyOrAdmin, ReadOnlyOrSafetyOfficer
from accounts.service_auth import IsCameraService, IsVestGateway
from rest_framework.response import Response
from rest_framework.views import APIView

from workers.models import Worker

from .models import Alert, AlertConfig, AlertSource, AlertType, Detection, Severity
from .rules import rule_for, rule_for_alert, rules_for_camera
from .serializers import (
    AlertConfigSerializer,
    AlertIngestSerializer,
    AlertSerializer,
    AlertSimulateSerializer,
    CameraEventSerializer,
    DetectionSerializer,
)


class DashboardStatsView(APIView):
    permission_classes = [IsViewer]

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_workers = Worker.objects.count()
        active_workers = Worker.objects.filter(is_active=True).count()
        unresolved = Alert.objects.filter(is_resolved=False)
        unresolved_alerts = unresolved.count()
        critical_alerts = unresolved.filter(severity=Severity.CRITICAL).count()
        total_alerts_today = Alert.objects.filter(timestamp__gte=start_of_day).count()

        counts_qs = (
            Alert.objects.filter(is_resolved=False)
            .values("alert_type")
            .annotate(c=Count("id"))
        )
        counts_map = {row["alert_type"]: row["c"] for row in counts_qs}
        alerts_by_type = {choice.value: counts_map.get(choice.value, 0) for choice in AlertType}

        return Response(
            {
                "total_workers": total_workers,
                "active_workers": active_workers,
                "total_alerts_today": total_alerts_today,
                "unresolved_alerts": unresolved_alerts,
                "critical_alerts": critical_alerts,
                "alerts_by_type": alerts_by_type,
            }
        )


class AlertViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Alert.objects.select_related("worker").all()
    serializer_class = AlertSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]

    def get_queryset(self):
        qs = super().get_queryset()
        is_resolved = self.request.query_params.get("is_resolved")
        if is_resolved is not None:
            val = str(is_resolved).lower()
            if val in ("true", "1", "yes"):
                qs = qs.filter(is_resolved=True)
            elif val in ("false", "0", "no"):
                qs = qs.filter(is_resolved=False)
        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = AlertSerializer(serializer.instance)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(AlertSerializer(serializer.instance).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["is_resolved", "resolved_at"])
        return Response(AlertSerializer(alert).data)

    @action(detail=False, methods=["post"], url_path="simulate")
    def simulate(self, request):
        serializer = AlertSimulateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)


def _suppressed(rule):
    return Response(
        {"status": "suppressed", "alert_type": rule.alert_type, "reason": "Alert type disabled by rule."},
        status=status.HTTP_202_ACCEPTED,
    )


class AlertIngestView(APIView):
    """POST alerts from a vest gateway, identifying the worker by vest_id."""

    permission_classes = [IsVestGateway]

    def post(self, request, *args, **kwargs):
        serializer = AlertIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = Worker.objects.filter(
            vest_id=serializer.validated_data["vest_id"], is_active=True
        ).select_related("zone").first()
        rule = rule_for(serializer.validated_data["alert_type"], worker.zone if worker else None)
        if not rule.is_enabled:
            return _suppressed(rule)
        alert = serializer.save()
        return Response(
            AlertSerializer(alert, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CameraEventView(APIView):
    """POST a confirmed event from an authenticated camera worker.

    Responses: 201 stored, 200 already stored (same ``event_id``), 202
    suppressed by a disabled rule. A camera treats all three as delivered.
    """

    permission_classes = [IsCameraService]

    def post(self, request, *args, **kwargs):
        serializer = CameraEventSerializer(
            data=request.data, context={"service_token": request.auth}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = Alert.objects.filter(event_id=data["event_id"]).first()
        if existing:
            return Response(AlertSerializer(existing).data, status=status.HTTP_200_OK)

        alert = Alert(
            alert_type=data["alert_type"],
            severity=data["severity"],
            source=AlertSource.AI_CAMERA,
            description=data["description"],
            camera_id=data["camera_id"],
            confidence=data["confidence"],
            event_id=data["event_id"],
        )
        rule = rule_for_alert(alert)
        if not rule.is_enabled:
            return _suppressed(rule)
        try:
            with transaction.atomic():
                alert.save()
        except IntegrityError:
            existing = Alert.objects.filter(event_id=data["event_id"]).first()
            if existing is None:
                raise
            return Response(AlertSerializer(existing).data, status=status.HTTP_200_OK)
        return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)


class CameraConfigView(APIView):
    """GET the effective rules for one camera, so the edge applies saved settings.

    Inactivity uses ``threshold_seconds`` as its stationary timeout.
    """

    permission_classes = [IsCameraService]

    def get(self, request, *args, **kwargs):
        camera_id = (request.query_params.get("camera_id") or "").strip()
        if not camera_id:
            return Response({"detail": "camera_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.auth.allows_camera(camera_id):
            return Response(
                {"detail": "This device token may not read this camera's configuration."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from sitemap.models import Zone

        zone = Zone.objects.for_camera(camera_id).first()
        rules = rules_for_camera(camera_id)
        return Response(
            {
                "camera_id": camera_id,
                "zone": zone.name if zone else None,
                "rules": {
                    t: {"is_enabled": r.is_enabled, "threshold_seconds": r.threshold_seconds}
                    for t, r in rules.items()
                },
            }
        )


class DetectionViewSet(viewsets.ModelViewSet):
    queryset = Detection.objects.select_related("worker").all()
    serializer_class = DetectionSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsCameraService()]
        return [IsViewer()]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["service_token"] = self.request.auth if self.action == "create" else None
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        camera_id = self.request.query_params.get("camera_id")
        if camera_id:
            qs = qs.filter(camera_id=camera_id)
        class_name = self.request.query_params.get("class_name")
        if class_name:
            qs = qs.filter(class_name=class_name)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            day = parse_date(start_date)
            if day:
                start = timezone.make_aware(datetime.combine(day, time.min))
                qs = qs.filter(frame_timestamp__gte=start)
        if end_date:
            day = parse_date(end_date)
            if day:
                end = timezone.make_aware(datetime.combine(day, time.max))
                qs = qs.filter(frame_timestamp__lte=end)
        return qs


class AlertConfigViewSet(viewsets.ModelViewSet):
    queryset = AlertConfig.objects.select_related("zone").all()
    serializer_class = AlertConfigSerializer
    permission_classes = [ReadOnlyOrAdmin]
