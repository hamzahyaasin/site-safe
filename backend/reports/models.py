from django.conf import settings
from django.db import models


class Report(models.Model):
    class ReportType(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident Report"
        COMPLIANCE = "COMPLIANCE", "Compliance Report"

    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    date_from = models.DateField()
    date_to = models.DateField()
    file = models.FileField(upload_to="reports/")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_report_type_display()} ({self.date_from} – {self.date_to})"
