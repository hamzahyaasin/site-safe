from django.conf import settings
from django.db import models


class Report(models.Model):
    class ReportType(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident Report"
        COMPLIANCE = "COMPLIANCE", "Safety Performance Report"

    class Format(models.TextChoices):
        DOCX = "DOCX", "Word (.docx)"
        PDF = "PDF", "PDF"

    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    file_format = models.CharField(max_length=8, choices=Format.choices, default=Format.DOCX)
    date_from = models.DateField()
    date_to = models.DateField()
    # Camera snapshots embedded as evidence (FR-34). They can show people, so
    # the history says which reports carry them.
    includes_evidence = models.BooleanField(default=False)
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
