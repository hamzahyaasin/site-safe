from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts.alert_config_urls import alert_config_urlpatterns
from alerts.urls import detection_urlpatterns
from alerts.views import (
    AlertIngestView,
    AlertViewSet,
    CameraActivityView,
    CameraConfigView,
    CameraCountView,
    CameraEventView,
    CameraFrameView,
    CameraLatestFrameView,
    CameraListView,
    DashboardStatsView,
)
from sitemap.urls import area_urlpatterns, permit_urlpatterns
from sitemap.views import CameraMapView, CameraPlacementView
from workers.urls import activity_urlpatterns, vest_urlpatterns

from .jwt_views import PublicTokenObtainPairView, PublicTokenRefreshView

router = DefaultRouter()
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", PublicTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/alerts/ingest/", AlertIngestView.as_view(), name="alert-ingest"),
    path("api/v1/camera-events/", CameraEventView.as_view(), name="camera-events"),
    path("api/v1/camera-config/", CameraConfigView.as_view(), name="camera-config"),
    path("api/v1/camera-activity/", CameraActivityView.as_view(), name="camera-activity"),
    path("api/v1/camera-frames/", CameraFrameView.as_view(), name="camera-frames"),
    path("api/v1/camera-frames/latest/", CameraLatestFrameView.as_view(), name="camera-latest-frame"),
    path("api/v1/camera-counts/", CameraCountView.as_view(), name="camera-counts"),
    path("api/v1/cameras/", CameraListView.as_view(), name="cameras"),
    path("api/v1/camera-map/", CameraMapView.as_view(), name="camera-map"),
    path("api/v1/camera-map/<str:camera_id>/", CameraPlacementView.as_view(), name="camera-placement"),
    path("api/workers/", include("workers.urls")),
    path("api/v1/vests/", include((vest_urlpatterns, "workers"), namespace="vests")),
    path("api/v1/activity/", include((activity_urlpatterns, "workers"), namespace="activity")),
    path("api/v1/detections/", include((detection_urlpatterns, "alerts"), namespace="detections")),
    path("api/v1/alert-config/", include((alert_config_urlpatterns, "alerts"), namespace="alert-config")),
    path("api/v1/zones/", include("sitemap.urls")),
    path("api/v1/hot-work-permits/", include((permit_urlpatterns, "sitemap"), namespace="permits")),
    path("api/v1/camera-areas/", include((area_urlpatterns, "sitemap"), namespace="camera-areas")),
    path("api/v1/fcm-tokens/", include("accounts.urls")),
    path("api/v1/profile/", include("accounts.profile_urls")),
    path("api/v1/reports/", include("reports.urls")),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
