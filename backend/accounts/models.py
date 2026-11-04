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


class ServiceToken(models.Model):
    """Credential for a non-human producer: a camera worker or a vest gateway.

    Cameras and gateways used to authenticate as a human admin account, which
    put a real password in source and let a compromised edge process do
    anything an admin could. A service token is scoped to the one kind of data
    it produces and cannot use any human endpoint. Only a SHA-256 hash of the
    key is stored; the plaintext is shown once when the token is created.
    """

    class Kind(models.TextChoices):
        CAMERA = "CAMERA", "Camera worker"
        VEST_GATEWAY = "VEST_GATEWAY", "Vest gateway"
        GAS_MONITOR = "GAS_MONITOR", "Gas monitor"

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    key_prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    camera_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Camera tokens only: camera_ids this token may report for. Empty = any.",
    )
    is_simulator = models.BooleanField(
        default=False,
        help_text="Data from this token is test data: its alerts are marked SIMULATED.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.kind}{', simulator' if self.is_simulator else ''})"

    @staticmethod
    def hash_key(key: str) -> str:
        import hashlib

        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def issue(cls, name: str, kind: str, camera_ids=None, is_simulator=False):
        """Create a token and return (instance, plaintext_key)."""
        import secrets

        key = f"ss_{secrets.token_urlsafe(32)}"
        token = cls.objects.create(
            name=name,
            kind=kind,
            key_prefix=key[:12],
            key_hash=cls.hash_key(key),
            camera_ids=list(camera_ids or []),
            is_simulator=is_simulator,
        )
        return token, key

    def allows_camera(self, camera_id: str) -> bool:
        return not self.camera_ids or camera_id in self.camera_ids
