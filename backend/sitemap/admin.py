from django.contrib import admin

from .models import HotWorkPermit, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "risk_level", "max_occupancy", "is_active")
    list_filter = ("risk_level", "is_active")


@admin.register(HotWorkPermit)
class HotWorkPermitAdmin(admin.ModelAdmin):
    list_display = ("zone", "description", "starts_at", "ends_at", "revoked_at", "issued_by")
    list_filter = ("zone",)
