import uuid

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import datetime, time
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.negotiation import BaseContentNegotiation
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
    CameraActivitySerializer,
    CameraEventSerializer,
    DetectionSerializer,
)


def filter_local_dates(qs, field, request):
    """Apply ?start_date= / ?end_date= (YYYY-MM-DD, inclusive) as whole days in ?tz=.

    Report periods are chosen as calendar days by the user, so the bounds
    must be that user's midnight, not the server's.
    """
    from datetime import timedelta

    tz = _request_timezone(request)
    start = parse_date(request.query_params.get("start_date") or "")
    end = parse_date(request.query_params.get("end_date") or "")
    if start:
        qs = qs.filter(**{f"{field}__gte": datetime.combine(start, time.min, tzinfo=tz)})
    if end:
        qs = qs.filter(**{f"{field}__lt": datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)})
    return qs


def _request_timezone(request):
    """IANA zone from ?tz= (the browser's), else the server's TIME_ZONE."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    name = request.query_params.get("tz")
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return timezone.get_default_timezone()


class DashboardStatsView(APIView):
    """Dashboard figures computed only from stored records.

    Day and hour buckets use the caller's ``tz``. "On site" counts active
    workers whose vest is currently reporting; it is unknown for workers
    without vests. Simulated alerts are counted separately so a demo can
    be distinguished from real observations.
    """

    permission_classes = [IsViewer]

    def get(self, request, *args, **kwargs):
        from datetime import timedelta

        from django.db.models import Avg, DurationField, ExpressionWrapper, F, Q
        from django.db.models.functions import TruncDate, TruncHour

        from workers.presence import offline_after

        tz = _request_timezone(request)
        now = timezone.now()
        local_now = now.astimezone(tz)
        start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_yesterday = start_of_day - timedelta(days=1)
        week_start = start_of_day - timedelta(days=6)

        workers = Worker.objects.all()
        active = workers.filter(is_active=True)
        with_vest = active.filter(smart_vest__isnull=False)
        on_site = with_vest.filter(smart_vest__last_seen__gte=now - offline_after())

        unresolved = Alert.objects.filter(is_resolved=False)
        today = Alert.objects.filter(timestamp__gte=start_of_day)
        simulated = Q(source=AlertSource.SIMULATED)

        def by_type(qs):
            counts = dict(qs.values_list("alert_type").annotate(c=Count("id")))
            return {t.value: counts.get(t.value, 0) for t in AlertType}

        hourly_counts = {
            row["hour"].astimezone(tz).hour: row
            for row in today.annotate(hour=TruncHour("timestamp", tzinfo=tz))
            .values("hour")
            .annotate(count=Count("id"), simulated=Count("id", filter=simulated))
        }
        hourly = [
            {
                "hour": h,
                "count": hourly_counts.get(h, {}).get("count", 0),
                "simulated": hourly_counts.get(h, {}).get("simulated", 0),
            }
            for h in range(local_now.hour + 1)
        ]

        week = Alert.objects.filter(timestamp__gte=week_start)
        daily_counts = {
            row["day"]: row
            for row in week.annotate(day=TruncDate("timestamp", tzinfo=tz))
            .values("day")
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(is_resolved=True)),
                simulated=Count("id", filter=simulated),
            )
        }
        daily = []
        for i in range(7):
            day = (week_start + timedelta(days=i)).date()
            row = daily_counts.get(day, {})
            daily.append(
                {
                    "date": day.isoformat(),
                    "total": row.get("total", 0),
                    "resolved": row.get("resolved", 0),
                    "simulated": row.get("simulated", 0),
                }
            )

        resolved_week = week.filter(is_resolved=True, resolved_at__isnull=False)
        mean_resolution = resolved_week.aggregate(
            avg=Avg(
                ExpressionWrapper(F("resolved_at") - F("timestamp"), output_field=DurationField())
            )
        )["avg"]

        return Response(
            {
                "timezone": str(tz),
                "total_workers": workers.count(),
                "active_workers": active.count(),
                "workers_with_vest": with_vest.count(),
                "workers_on_site": on_site.count(),
                "total_alerts_today": today.count(),
                "simulated_alerts_today": today.filter(simulated).count(),
                "alerts_yesterday": Alert.objects.filter(
                    timestamp__gte=start_of_yesterday, timestamp__lt=start_of_day
                ).count(),
                "unresolved_alerts": unresolved.count(),
                "critical_alerts": unresolved.filter(severity=Severity.CRITICAL).count(),
                "alerts_by_type": by_type(unresolved),
                "today_by_type": by_type(today),
                "hourly_today": hourly,
                "daily_7d": daily,
                "resolved_7d": resolved_week.count(),
                "mean_resolution_minutes_7d": (
                    round(mean_resolution.total_seconds() / 60, 1) if mean_resolution else None
                ),
            }
        )


class IgnoreAcceptHeader(BaseContentNegotiation):
    """Always render errors as JSON, whatever the client asks for.

    The snapshot endpoint returns a raw JPEG that bypasses renderers, and
    image clients send ``Accept: image/*``, which DRF would otherwise refuse
    with 406 before the view runs.
    """

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


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
        return filter_local_dates(qs, "timestamp", self.request)

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

    @action(detail=True, methods=["get"], url_path="snapshot", content_negotiation_class=IgnoreAcceptHeader)
    def snapshot(self, request, pk=None):
        """The alert's evidence JPEG, for the same users who may read the alert."""
        from django.http import FileResponse, Http404

        alert = self.get_object()
        if not alert.snapshot:
            raise Http404("This alert has no snapshot.")
        try:
            handle = alert.snapshot.open("rb")
        except FileNotFoundError as exc:
            raise Http404("The snapshot file is missing.") from exc
        response = FileResponse(handle, content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response

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
            smart_vest__vest_id=serializer.validated_data["vest_id"], is_active=True
        ).select_related("zone").first()
        rule = rule_for(serializer.validated_data["alert_type"], worker.zone if worker else None)
        if not rule.is_enabled:
            return _suppressed(rule)
        alert = serializer.save(simulated=request.auth.is_simulator)
        return Response(
            AlertSerializer(alert, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CameraEventView(APIView):
    """POST a confirmed event from an authenticated camera worker.

    Responses: 201 stored, 200 already stored (same ``event_id``), 202
    suppressed by a disabled rule. A camera treats all three as delivered.

    Alert evidence (FR-29): ``model_version`` names the weights, and
    ``snapshot`` is an optional base64-encoded JPEG in the same JSON body
    (validated by ``decode_snapshot``). The image is written only for a new
    event, so a retried or duplicate ``event_id`` never stores a second file,
    and it is dropped when ``ALERT_SNAPSHOTS_ENABLED`` is off.
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

        description = data["description"]
        worker = None
        if data["badge_code"]:
            worker = Worker.from_badge(data["badge_code"])
            description = (
                f"{description} (identified by QR badge)"
                if worker
                else f"{description} (QR badge not recognised)"
            )
        alert = Alert(
            alert_type=data["alert_type"],
            severity=data["severity"],
            source=AlertSource.SIMULATED if request.auth.is_simulator else AlertSource.AI_CAMERA,
            description=description,
            camera_id=data["camera_id"],
            confidence=data["confidence"],
            model_version=data["model_version"],
            event_id=data["event_id"],
            worker=worker,
        )
        rule = rule_for_alert(alert)
        if not rule.is_enabled:
            return _suppressed(rule)
        from django.conf import settings
        from django.core.files.base import ContentFile

        from sitemap.models import Zone

        from . import fire_policy

        fire_policy.apply(alert, Zone.objects.for_camera(alert.camera_id).first())
        if data["snapshot"] and settings.ALERT_SNAPSHOTS_ENABLED:
            # Written before the insert so the alert is broadcast once, with
            # its snapshot; a random name keeps files unguessable.
            alert.snapshot.save(f"{uuid.uuid4().hex}.jpg", ContentFile(data["snapshot"]), save=False)
        try:
            with transaction.atomic():
                alert.save()
        except Exception as exc:
            # Never leave an image without its alert. On IntegrityError a
            # concurrent delivery of the same event won the insert and keeps
            # its own image.
            if alert.snapshot:
                alert.snapshot.delete(save=False)
            if not isinstance(exc, IntegrityError):
                raise
            existing = Alert.objects.filter(event_id=data["event_id"]).first()
            if existing is None:
                raise
            return Response(AlertSerializer(existing).data, status=status.HTTP_200_OK)
        return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)


class CameraActivityView(APIView):
    """POST a sighting or idle start/end for a badge-identified person.

    Unknown or revoked badges are accepted and ignored (202), so a camera
    never retries them forever; simulator tokens are ignored too, so test
    data never enters attendance records.
    """

    permission_classes = [IsCameraService]

    def post(self, request, *args, **kwargs):
        from workers import activity

        serializer = CameraActivitySerializer(data=request.data, context={"service_token": request.auth})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        worker = Worker.from_badge(data["badge_code"])
        if worker is None or request.auth.is_simulator:
            return Response({"status": "ignored"}, status=status.HTTP_202_ACCEPTED)
        source = f"camera {data['camera_id']}"
        when = data["occurred_at"]
        if data["kind"] == "IDLE_START":
            activity.idle_start(worker, when, source)
        elif data["kind"] == "IDLE_END":
            activity.idle_end(worker, when, source)
        else:
            activity.record_seen(worker, when, source)
        return Response({"status": "recorded", "worker": worker.pk}, status=status.HTTP_200_OK)


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
