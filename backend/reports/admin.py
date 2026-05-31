from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "report_type", "date_from", "date_to", "created_by", "created_at")
    list_filter = ("report_type",)
    readonly_fields = ("created_at",)
