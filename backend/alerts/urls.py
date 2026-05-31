from rest_framework.routers import DefaultRouter

from .views import DetectionViewSet

router = DefaultRouter()
router.register(r"", DetectionViewSet, basename="detection")

urlpatterns = router.urls

detection_urlpatterns = urlpatterns
