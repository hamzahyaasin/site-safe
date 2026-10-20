from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action

from accounts.permissions import IsSafetyOfficer, ReadOnlyOrSafetyOfficer
from accounts.service_auth import IsVestGateway
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, SmartVest, Worker
from .mqtt_handlers import apply_vest_telemetry
from .serializers import (
    ActivityLogSerializer,
    SmartVestSerializer,
    VestTelemetrySerializer,
    WorkerSerializer,
)


def _timezone(request):
    from alerts.views import _request_timezone

    return _request_timezone(request)


def _parse_day(value, tz):
    if not value:
        return timezone.now().astimezone(tz).date()
    return parse_date(value)


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.select_related("zone", "smart_vest").all()
    serializer_class = WorkerSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]

    @action(detail=True, methods=["get", "post"], permission_classes=[IsSafetyOfficer])
    def badge(self, request, pk=None):
        """GET the QR badge payload to print; POST to reissue it, which
        revokes every previously printed badge for this worker."""
        worker = self.get_object()
        if request.method == "POST":
            worker.reissue_badge()
        return Response(
            {
                "worker": worker.pk,
                "name": worker.name,
                "role": worker.role,
                "payload": worker.badge_payload,
                "is_active": worker.is_active,
            }
        )


class SmartVestViewSet(viewsets.ModelViewSet):
    queryset = SmartVest.objects.select_related("worker").all()
    serializer_class = SmartVestSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]


class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.select_related("worker", "zone").all()
    serializer_class = ActivityLogSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        from alerts.views import filter_local_dates

        worker_id = self.request.query_params.get("worker_id")
        if worker_id:
            qs = qs.filter(worker_id=worker_id)
        return filter_local_dates(qs, "timestamp", self.request)

    def _worker(self, request):
        worker_id = request.query_params.get("worker_id")
        if not worker_id:
            return None, Response({"detail": "worker_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        worker = Worker.objects.filter(pk=worker_id).first()
        if worker is None:
            return None, Response({"detail": "Worker not found."}, status=status.HTTP_404_NOT_FOUND)
        return worker, None

    @action(detail=False, methods=["get"])
    def timeline(self, request):
        """One worker's day: sessions, idle periods and zone visits, with totals."""
        from .timeline import build_timeline

        worker, error = self._worker(request)
        if error:
            return error
        tz = _timezone(request)
        day = _parse_day(request.query_params.get("date"), tz)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_timeline(worker, day, tz))

    @action(detail=False, methods=["get"])
    def daily(self, request):
        """Per-worker, per-day totals over a date range (max 31 days); only days with activity."""
        from datetime import timedelta

        from .timeline import build_timeline

        tz = _timezone(request)
        first = _parse_day(request.query_params.get("start_date"), tz)
        last = _parse_day(request.query_params.get("end_date"), tz)
        if first is None or last is None or last < first:
            return Response({"detail": "start_date and end_date must be YYYY-MM-DD, in order."}, status=status.HTTP_400_BAD_REQUEST)
        if (last - first).days > 30:
            return Response({"detail": "At most 31 days per request."}, status=status.HTTP_400_BAD_REQUEST)
        rows = []
        worker_ids = set(
            ActivityLog.objects.filter(timestamp__lt=timezone.now()).values_list("worker_id", flat=True)
        )
        for worker in Worker.objects.filter(pk__in=worker_ids).order_by("name"):
            day = first
            while day <= last:
                t = build_timeline(worker, day, tz)
                if t["has_activity"]:
                    rows.append({k: t[k] for k in (
                        "worker", "worker_name", "date", "first_check_in", "last_check_out",
                        "on_site_minutes", "idle_minutes", "zone_minutes", "evidence_sources",
                    )} | {"sessions": len(t["sessions"]), "still_open": any(x["open"] for x in t["sessions"])})
                day += timedelta(days=1)
        return Response(rows)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Hours on site and idle for one worker-day (kept for older clients)."""
        from .timeline import build_timeline

        worker, error = self._worker(request)
        if error:
            return error
        tz = _timezone(request)
        day = _parse_day(request.query_params.get("date"), tz)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        t = build_timeline(worker, day, tz)
        return Response(
            {
                "worker_id": worker.pk,
                "date": t["date"],
                "worked_seconds": int(t["on_site_minutes"] * 60),
                "hours_worked": round(t["on_site_minutes"] / 60, 2),
                "idle_seconds": int(t["idle_minutes"] * 60),
                "idle_hours": round(t["idle_minutes"] / 60, 2),
            }
        )


class VestTelemetryView(APIView):
    """Receives periodic telemetry from Smart Vest via LoRa gateway.

    Payload: { vest_id, latitude, longitude, battery_level, sos_active }
    """

    permission_classes = [IsVestGateway]

    def post(self, request):
        serializer = VestTelemetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        vest_id = data.pop("vest_id", None)
        if not vest_id:
            return Response({"vest_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        vest = apply_vest_telemetry(vest_id, data, simulated=request.auth.is_simulator)
        if not vest:
            return Response({"error": "Unknown vest"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})
