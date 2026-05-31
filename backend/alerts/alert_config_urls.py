from rest_framework.routers import DefaultRouter

from .views import AlertConfigViewSet

router = DefaultRouter()
router.register(r"", AlertConfigViewSet, basename="alert-config")

urlpatterns = router.urls

alert_config_urlpatterns = urlpatterns
