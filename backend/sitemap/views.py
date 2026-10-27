from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone

from accounts.permissions import IsSafetyOfficer, ReadOnlyOrAdmin, ReadOnlyOrSafetyOfficer
from rest_framework.response import Response

from workers.models import Worker
from workers.serializers import WorkerSerializer

from .geofence import point_in_polygon
from .models import CameraArea, HotWorkPermit, Zone
from .serializers import CameraAreaSerializer, HotWorkPermitSerializer, ZoneDetailSerializer, ZoneSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.prefetch_related("workers").all()
    permission_classes = [ReadOnlyOrAdmin]

    def get_serializer_class(self):
        if self.action in ("retrieve", "list"):
            return ZoneDetailSerializer
        return ZoneSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            val = str(is_active).lower()
            if val in ("true", "1", "yes"):
                qs = qs.filter(is_active=True)
            elif val in ("false", "0", "no"):
                qs = qs.filter(is_active=False)
        return qs

    @action(detail=True, methods=["get"])
    def workers(self, request, pk=None):
        zone = self.get_object()
        workers = Worker.objects.filter(zone=zone).select_related("zone").order_by("name")
        serializer = WorkerSerializer(workers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def check_point(self, request, pk=None):
        zone = self.get_object()
        lat = request.data.get("lat")
        lng = request.data.get("lng")

        if lat is None or lng is None:
            return Response(
                {"detail": "lat and lng are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            return Response(
                {"detail": "lat and lng must be numeric."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inside = point_in_polygon(lat_f, lng_f, zone.boundaries)
        return Response(
            {
                "zone_id": zone.id,
                "zone_name": zone.name,
                "lat": lat_f,
                "lng": lng_f,
                "inside": inside,
            }
        )


class HotWorkPermitViewSet(viewsets.ModelViewSet):
    """Hot-work permits. Safety Officers issue and revoke; everyone can read.

    Permits are revoked rather than deleted so the alert history keeps the
    permit each downgraded fire/smoke alert relied on.
    """

    serializer_class = HotWorkPermitSerializer
    permission_classes = [ReadOnlyOrSafetyOfficer]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = HotWorkPermit.objects.select_related("zone", "issued_by")
        state = self.request.query_params.get("state")
        now = timezone.now()
        if state == "active":
            qs = qs.active_at(now)
        elif state == "current":  # active or still to come
            qs = qs.filter(revoked_at__isnull=True, ends_at__gt=now)
        zone = self.request.query_params.get("zone")
        if zone:
            qs = qs.filter(zone_id=zone)
        return qs

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if self.get_object().revoked_at:
            return Response({"detail": "A revoked permit cannot be changed."}, status=status.HTTP_400_BAD_REQUEST)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsSafetyOfficer])
    def revoke(self, request, pk=None):
        permit = self.get_object()
        if permit.revoked_at is None:
            permit.revoked_at = timezone.now()
            permit.save(update_fields=["revoked_at"])
        return Response(HotWorkPermitSerializer(permit).data)


class CameraAreaViewSet(viewsets.ModelViewSet):
    """Danger areas drawn on camera pictures. Admins edit; signed-in users read (``?camera_id=``)."""

    queryset = CameraArea.objects.all()
    serializer_class = CameraAreaSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        camera_id = self.request.query_params.get("camera_id")
        return qs.filter(camera_id=camera_id) if camera_id else qs
