from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ActivityLogViewSet, SmartVestViewSet, VestTelemetryView, WorkerViewSet

worker_router = DefaultRouter()
worker_router.register(r"", WorkerViewSet, basename="worker")

vest_router = DefaultRouter()
vest_router.register(r"", SmartVestViewSet, basename="vest")

activity_router = DefaultRouter()
activity_router.register(r"", ActivityLogViewSet, basename="activity")

urlpatterns = worker_router.urls

vest_urlpatterns = [
    path("telemetry/", VestTelemetryView.as_view(), name="vest-telemetry"),
    *vest_router.urls,
]

activity_urlpatterns = activity_router.urls
