from django.contrib import admin

from .models import Worker


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("name", "vest_id", "zone", "is_active", "created_at")
    list_filter = ("is_active", "zone")
    search_fields = ("name", "vest_id")
