from django.contrib import admin

from .models import GasMonitor, HotWorkPermit, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "risk_level", "max_occupancy", "is_active")
    list_filter = ("risk_level", "is_active")


@admin.register(GasMonitor)
class GasMonitorAdmin(admin.ModelAdmin):
    list_display = ("monitor_id", "name", "zone", "gas_ppm", "is_online", "last_seen")
    list_filter = ("zone",)


@admin.register(HotWorkPermit)
class HotWorkPermitAdmin(admin.ModelAdmin):
    list_display = ("zone", "description", "starts_at", "ends_at", "revoked_at", "issued_by")
    list_filter = ("zone",)
