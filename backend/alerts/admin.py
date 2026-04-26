from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "worker",
        "alert_type",
        "severity",
        "source",
        "is_resolved",
        "timestamp",
        "resolved_at",
    )
    list_filter = ("alert_type", "severity", "source", "is_resolved")
    search_fields = ("worker__name", "worker__vest_id", "description")
    raw_id_fields = ("worker",)
