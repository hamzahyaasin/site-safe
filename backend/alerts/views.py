from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workers.models import Worker

from .models import Alert, AlertType, Severity
from .serializers import (
    AlertIngestSerializer,
    AlertSerializer,
    AlertSimulateSerializer,
)


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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


class AlertIngestView(APIView):
    """POST alerts from the AI module (unauthenticated; protect in production)."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = AlertIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        return Response(
            AlertSerializer(alert, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
