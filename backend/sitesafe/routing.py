from django.urls import re_path

from alerts import consumers

websocket_urlpatterns = [
    re_path(r"ws/dashboard/(?P<site_id>[^/]+)/$", consumers.DashboardConsumer.as_asgi()),
    re_path(r"ws/dashboard/$", consumers.DashboardConsumer.as_asgi()),
]
