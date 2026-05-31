from django.urls import path

from .views import GenerateReportView, ReportDownloadView, ReportListView

urlpatterns = [
    path("", ReportListView.as_view(), name="report-list"),
    path("generate/", GenerateReportView.as_view(), name="report-generate"),
    path("<int:pk>/download/", ReportDownloadView.as_view(), name="report-download"),
]
