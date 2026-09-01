from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.permissions import ReadOnlyOrSafetyOfficer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, SmartVest, Worker
from .mqtt_handlers import apply_vest_telemetry
from .serializers import ActivityLogSerializer, SmartVestSerializer, WorkerSerializer


def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    return start, end


def _filter_by_date_range(qs, param_prefix, start_date, end_date):
    if start_date:
        day = parse_date(start_date)
        if day:
            qs = qs.filter(**{f"{param_prefix}__gte": _day_bounds(day)[0]})
    if end_date:
        day = parse_date(end_date)
        if day:
            qs = qs.filter(**{f"{param_prefix}__lte": _day_bounds(day)[1]})
    return qs


def compute_activity_summary(worker_id, day):
    start, end = _day_bounds(day)
    now = timezone.now()

    logs = ActivityLog.objects.filter(
        worker_id=worker_id,
        timestamp__gte=start,
        timestamp__lte=end,
    ).order_by("timestamp")

    worked_seconds = 0.0
    idle_seconds = 0.0
    check_in_time = None
    idle_start_time = None

    for log in logs:
        if log.action == ActivityLog.Action.CHECK_IN:
            check_in_time = log.timestamp
        elif log.action == ActivityLog.Action.CHECK_OUT and check_in_time:
            worked_seconds += (log.timestamp - check_in_time).total_seconds()
            check_in_time = None
        elif log.action == ActivityLog.Action.IDLE_START:
            idle_start_time = log.timestamp
        elif log.action == ActivityLog.Action.IDLE_END and idle_start_time:
            idle_seconds += (log.timestamp - idle_start_time).total_seconds()
            idle_start_time = None

    cap = min(now, end) if day == now.date() else end
    if check_in_time:
        worked_seconds += (cap - check_in_time).total_seconds()
    if idle_start_time:
        idle_seconds += (cap - idle_start_time).total_seconds()

    return {
        "worker_id": worker_id,
        "date": day.isoformat(),
        "worked_seconds": int(worked_seconds),
        "hours_worked": round(worked_seconds / 3600, 2),
        "idle_seconds": int(idle_seconds),
        "idle_hours": round(idle_seconds / 3600, 2),
    }


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.select_related("zone").all()
    serializer_class = WorkerSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]


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
        worker_id = self.request.query_params.get("worker_id")
        if worker_id:
            qs = qs.filter(worker_id=worker_id)
        return _filter_by_date_range(
            qs,
            "timestamp",
            self.request.query_params.get("start_date"),
            self.request.query_params.get("end_date"),
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        worker_id = request.query_params.get("worker_id")
        if not worker_id:
            return Response(
                {"detail": "worker_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Worker.objects.filter(pk=worker_id).exists():
            return Response(
                {"detail": "Worker not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        date_str = request.query_params.get("date")
        day = parse_date(date_str) if date_str else timezone.localdate()
        if day is None:
            return Response(
                {"detail": "date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(compute_activity_summary(worker_id, day))


class VestTelemetryView(APIView):
    """Receives periodic telemetry from Smart Vest via LoRa gateway.

    Payload: { vest_id, latitude, longitude, battery_level, sos_active }
    """

    permission_classes = [AllowAny]  # gateway auth in production

    def post(self, request):
        vest_id = request.data.get("vest_id")
        vest = apply_vest_telemetry(vest_id, request.data)
        if not vest:
            return Response({"error": "Unknown vest"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})
