from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import ReadOnlyOrAdmin
from rest_framework.response import Response

from workers.models import Worker
from workers.serializers import WorkerSerializer

from .geofence import point_in_polygon
from .models import Zone
from .serializers import ZoneDetailSerializer, ZoneSerializer


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
