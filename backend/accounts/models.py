from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class Role(models.TextChoices):
    """Site-Safe access roles.

    Ordered from most to least privileged; see `Role.rank` for the comparison
    used by the permission classes.
    """

    ADMIN = "ADMIN", "Admin"
    SAFETY_OFFICER = "SAFETY_OFFICER", "Safety Officer"
    VIEWER = "VIEWER", "Viewer"

    @classmethod
    def rank(cls, role: str) -> int:
        """Higher rank means more privilege. Unknown roles rank lowest."""
        return {cls.ADMIN: 3, cls.SAFETY_OFFICER: 2, cls.VIEWER: 1}.get(role, 0)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user for Site-Safe: email login, optional full name, staff/admin flags.
    """

    email = models.EmailField("email address", unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.SAFETY_OFFICER,
        help_text="Determines which API operations this user may perform.",
    )
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    @property
    def role_rank(self) -> int:
        # Django superusers and the legacy is_admin flag keep full access even
        # if their role column was never populated, so existing accounts do not
        # lose privileges when roles are introduced.
        if self.is_superuser or self.is_admin:
            return Role.rank(Role.ADMIN)
        return Role.rank(self.role)

    def has_role_at_least(self, role: str) -> bool:
        return self.role_rank >= Role.rank(role)


class FCMToken(models.Model):
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="fcm_tokens",
    )
    token = models.TextField(unique=True)
    device_name = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.device_name or 'device'}"


class UserPreferences(models.Model):
    user = models.OneToOneField(
        "User",
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    notify_push = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"
