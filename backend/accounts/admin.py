from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import ServiceToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff", "is_admin", "is_active", "is_superuser", "date_joined")
    list_filter = ("is_staff", "is_admin", "is_active", "is_superuser")
    search_fields = ("email", "full_name")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password", "full_name")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_admin", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "is_staff", "is_admin", "is_superuser"),
            },
        ),
    )


@admin.register(ServiceToken)
class ServiceTokenAdmin(admin.ModelAdmin):
    """Tokens are issued with ``manage.py create_service_token``; admin is for review and revocation."""

    list_display = ("name", "kind", "key_prefix", "is_active", "last_used_at", "created_at")
    list_filter = ("kind", "is_active")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "last_used_at")

    def has_add_permission(self, request):
        return False
