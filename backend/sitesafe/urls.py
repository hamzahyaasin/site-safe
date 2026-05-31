from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts.urls import detection_urlpatterns
from alerts.views import AlertIngestView, AlertViewSet, DashboardStatsView
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
    path("api/workers/", include("workers.urls")),
    path("api/v1/vests/", include((vest_urlpatterns, "workers"), namespace="vests")),
    path("api/v1/activity/", include((activity_urlpatterns, "workers"), namespace="activity")),
    path("api/v1/detections/", include((detection_urlpatterns, "alerts"), namespace="detections")),
    path("api/v1/zones/", include("sitemap.urls")),
    path("api/v1/fcm-tokens/", include("accounts.urls")),
    path("api/", include(router.urls)),
]
