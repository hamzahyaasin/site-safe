from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import CameraAreaViewSet, GasMonitorTelemetryView, GasMonitorViewSet, HotWorkPermitViewSet, ZoneViewSet

router = DefaultRouter()
router.register(r"", ZoneViewSet, basename="zone")

urlpatterns = router.urls

permit_router = DefaultRouter()
permit_router.register(r"", HotWorkPermitViewSet, basename="hot-work-permit")
permit_urlpatterns = permit_router.urls

area_router = DefaultRouter()
area_router.register(r"", CameraAreaViewSet, basename="camera-area")
area_urlpatterns = area_router.urls

gas_router = DefaultRouter()
gas_router.register(r"", GasMonitorViewSet, basename="gas-monitor")
gas_monitor_urlpatterns = [
    path("telemetry/", GasMonitorTelemetryView.as_view(), name="gas-monitor-telemetry"),
    *gas_router.urls,
]
