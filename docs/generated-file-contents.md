# Site-Safe — full contents of project files

Excludes: `backend/.venv/`, `**/__pycache__/`, `backend/.env`, and this file.
Copy `backend/.env.example` to `backend/.env` and edit values.


========================================================================
## FILE: .gitignore
========================================================================
.env
__pycache__/
*.pyc
.venv/
db.sqlite3

========================================================================
## FILE: ai-module/ppe_dataset/.gitkeep
========================================================================


========================================================================
## FILE: ai-module/requirements-vision.txt
========================================================================
ultralytics>=8.3.0
opencv-python>=4.8.0

========================================================================
## FILE: ai-module/scripts/inference_webcam.py
========================================================================
#!/usr/bin/env python3
"""
Webcam inference: YOLO + OpenCV, JSON per frame (violations by regex on class names).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


def ai_module_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_weights() -> Path:
    return ai_module_root() / "runs" / "train" / "ppe_yolov10n" / "weights" / "best.pt"


def detections_from_result(result) -> list[dict]:
    names = result.names
    boxes = result.boxes
    out: list[dict] = []
    if boxes is None or len(boxes) == 0:
        return out

    xyxy = boxes.xyxy.cpu().tolist()
    confs = boxes.conf.cpu().tolist()
    clss = boxes.cls.cpu().int().tolist()
    for i, cid in enumerate(clss):
        name = str(names[int(cid)])
        out.append(
            {
                "class": name,
                "class_id": int(cid),
                "confidence": round(float(confs[i]), 4),
                "xyxy": [round(float(x), 2) for x in xyxy[i]],
            }
        )
    return out


def filter_violations(detections: list[dict], pattern: re.Pattern | None) -> list[dict]:
    if pattern is None:
        return []
    return [d for d in detections if pattern.search(d["class"])]


def counts_by_class(detections: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in detections:
        c = d["class"]
        counts[c] = counts.get(c, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YOLO webcam inference + JSON violation summary.")
    p.add_argument(
        "--weights",
        type=Path,
        default=default_weights(),
        help="Path to trained weights.",
    )
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument(
        "--violation-pattern",
        type=str,
        default=r"no[-_]?|missing|without|unsafe|violation|non[-_]?compliance",
    )
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--device", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.chdir(ai_module_root())

    weights = args.weights.resolve()
    if not weights.is_file():
        print(f"Weights not found: {weights}", file=sys.stderr)
        sys.exit(1)

    violation_re: re.Pattern | None
    if args.violation_pattern.strip():
        violation_re = re.compile(args.violation_pattern, re.IGNORECASE)
    else:
        violation_re = None

    model = YOLO(str(weights))
    predict_kw: dict = dict(stream=False, verbose=False, conf=args.conf, imgsz=args.imgsz)
    if args.device is not None:
        predict_kw["device"] = args.device

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Could not open camera index {args.camera}", file=sys.stderr)
        sys.exit(1)

    frame_index = 0
    print("Streaming… Press 'q' to quit.", file=sys.stderr)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            t0 = time.perf_counter()
            results = model.predict(frame, **predict_kw)
            infer_ms = round((time.perf_counter() - t0) * 1000, 2)

            result = results[0]
            detections = detections_from_result(result)
            violations = filter_violations(detections, violation_re)

            summary = {
                "frame": frame_index,
                "inference_ms": infer_ms,
                "has_violations": len(violations) > 0,
                "violation_count": len(violations),
                "violations": violations,
                "detection_count": len(detections),
                "counts_by_class": counts_by_class(detections),
            }
            print(json.dumps(summary), flush=True)

            annotated = result.plot()
            cv2.imshow("Site-Safe PPE (q to quit)", annotated)
            frame_index += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

========================================================================
## FILE: ai-module/scripts/train_yolov10_ppe.py
========================================================================
#!/usr/bin/env python3
"""
Train Ultralytics YOLOv10n on a PPE dataset (YOLO format).

Dataset: <ai-module>/ppe_dataset/data.yaml
Training outputs: <ai-module>/runs/train/<name>/
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ultralytics import YOLO


def ai_module_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_data_yaml() -> Path:
    return ai_module_root() / "ppe_dataset" / "data.yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLOv10n on PPE dataset (Ultralytics).")
    p.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to data.yaml (default: ppe_dataset/data.yaml inside ai-module).",
    )
    p.add_argument("--weights", type=str, default="yolov10n.pt", help="Initial weights / model name.")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument(
        "--project",
        type=str,
        default="runs/train",
        help="Project dir relative to ai-module (Ultralytics: project/name/).",
    )
    p.add_argument("--name", type=str, default="ppe_yolov10n", help="Run name.")
    p.add_argument("--device", type=str, default=None, help="e.g. 0, cpu, mps — default: auto.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = ai_module_root()
    os.chdir(root)

    data_path = (args.data or default_data_yaml()).resolve()
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset config not found: {data_path}")

    model = YOLO(args.weights)
    train_kw = dict(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
    )
    if args.device is not None:
        train_kw["device"] = args.device

    model.train(**train_kw)


if __name__ == "__main__":
    main()

========================================================================
## FILE: backend/.env.example
========================================================================
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
DB_NAME=sitesafe
DB_USER=sitesafe
DB_PASSWORD=sitesafe
DB_HOST=localhost
DB_PORT=5432

========================================================================
## FILE: backend/accounts/__init__.py
========================================================================


========================================================================
## FILE: backend/accounts/admin.py
========================================================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active", "is_superuser", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )

========================================================================
## FILE: backend/accounts/apps.py
========================================================================
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

========================================================================
## FILE: backend/accounts/managers.py
========================================================================
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email address must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

========================================================================
## FILE: backend/accounts/migrations/0001_initial.py
========================================================================
# Generated by Django 6.0 on 2026-04-13

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
    ]

========================================================================
## FILE: backend/accounts/migrations/__init__.py
========================================================================


========================================================================
## FILE: backend/accounts/models.py
========================================================================
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user for Site-Safe. Uses AbstractBaseUser for credentials
    and PermissionsMixin for is_staff, groups, and Django admin support.
    """

    email = models.EmailField("email address", unique=True, db_index=True)
    is_staff = models.BooleanField(default=False)
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

========================================================================
## FILE: backend/accounts/tests.py
========================================================================
from django.test import TestCase

# Create your tests here.

========================================================================
## FILE: backend/accounts/views.py
========================================================================
from django.shortcuts import render

# Create your views here.

========================================================================
## FILE: backend/alerts/__init__.py
========================================================================


========================================================================
## FILE: backend/alerts/admin.py
========================================================================
from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "worker", "alert_type", "severity", "timestamp", "is_resolved")
    list_filter = ("alert_type", "severity", "is_resolved")
    search_fields = ("worker__name", "worker__vest_id")
    raw_id_fields = ("worker",)

========================================================================
## FILE: backend/alerts/apps.py
========================================================================
from django.apps import AppConfig


class AlertsConfig(AppConfig):
    name = 'alerts'

========================================================================
## FILE: backend/alerts/migrations/0001_initial.py
========================================================================
# Generated by Django 6.0 on 2026-04-13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("workers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "alert_type",
                    models.CharField(
                        choices=[
                            ("PPE_VIOLATION", "PPE violation"),
                            ("FALL", "Fall"),
                            ("GAS", "Gas"),
                            ("HEAT", "Heat"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("MEDIUM", "Medium"),
                            ("HIGH", "High"),
                        ],
                        max_length=16,
                    ),
                ),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("is_resolved", models.BooleanField(default=False)),
                (
                    "worker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="workers.worker",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
    ]

========================================================================
## FILE: backend/alerts/migrations/__init__.py
========================================================================


========================================================================
## FILE: backend/alerts/models.py
========================================================================
from django.db import models


class AlertType(models.TextChoices):
    PPE_VIOLATION = "PPE_VIOLATION", "PPE violation"
    FALL = "FALL", "Fall"
    GAS = "GAS", "Gas"
    HEAT = "HEAT", "Heat"


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class Alert(models.Model):
    worker = models.ForeignKey(
        "workers.Worker",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    alert_type = models.CharField(
        max_length=32,
        choices=AlertType.choices,
    )
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
    )
    timestamp = models.DateTimeField(db_index=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.alert_type} — {self.worker.vest_id} @ {self.timestamp}"

========================================================================
## FILE: backend/alerts/serializers.py
========================================================================
from django.utils import timezone
from rest_framework import serializers

from workers.models import Worker

from .models import Alert, AlertType, Severity


class AlertSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(required=False)

    class Meta:
        model = Alert
        fields = (
            "id",
            "worker",
            "alert_type",
            "severity",
            "timestamp",
            "is_resolved",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data.setdefault("timestamp", timezone.now())
        return super().create(validated_data)


class AlertIngestSerializer(serializers.Serializer):
    """Payload from the AI / edge module (identifies worker by vest_id)."""

    vest_id = serializers.CharField(max_length=64)
    alert_type = serializers.ChoiceField(choices=AlertType.choices)
    severity = serializers.ChoiceField(choices=Severity.choices)
    timestamp = serializers.DateTimeField(required=False)
    is_resolved = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        vest_id = validated_data.pop("vest_id")
        validated_data.setdefault("timestamp", timezone.now())
        try:
            worker = Worker.objects.get(vest_id=vest_id, is_active=True)
        except Worker.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"vest_id": "No active worker found with this vest_id."}
            ) from exc
        return Alert.objects.create(worker=worker, **validated_data)

========================================================================
## FILE: backend/alerts/tests.py
========================================================================
from django.test import TestCase

# Create your tests here.

========================================================================
## FILE: backend/alerts/views.py
========================================================================
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alert
from .serializers import AlertIngestSerializer, AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("worker").all()
    serializer_class = AlertSerializer


class AlertIngestView(APIView):
    """POST alerts from the AI module (unauthenticated; protect in production)."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = AlertIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        return Response(
            AlertSerializer(alert, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

========================================================================
## FILE: backend/manage.py
========================================================================
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitesafe.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

========================================================================
## FILE: backend/requirements.txt
========================================================================
django>=6.0,<7
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
psycopg2-binary>=2.9
django-cors-headers>=4.4
python-dotenv>=1.0

========================================================================
## FILE: backend/sitemap/__init__.py
========================================================================


========================================================================
## FILE: backend/sitemap/admin.py
========================================================================
from django.contrib import admin

# Register your models here.

========================================================================
## FILE: backend/sitemap/apps.py
========================================================================
from django.apps import AppConfig


class SitemapConfig(AppConfig):
    name = 'sitemap'

========================================================================
## FILE: backend/sitemap/migrations/__init__.py
========================================================================


========================================================================
## FILE: backend/sitemap/models.py
========================================================================
from django.db import models

# Create your models here.

========================================================================
## FILE: backend/sitemap/tests.py
========================================================================
from django.test import TestCase

# Create your tests here.

========================================================================
## FILE: backend/sitemap/views.py
========================================================================
from django.shortcuts import render

# Create your views here.

========================================================================
## FILE: backend/sitesafe/__init__.py
========================================================================


========================================================================
## FILE: backend/sitesafe/asgi.py
========================================================================
"""
ASGI config for sitesafe project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitesafe.settings')

application = get_asgi_application()

========================================================================
## FILE: backend/sitesafe/settings.py
========================================================================
"""
Django settings for Site-Safe backend (sitesafe project).
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-set-SECRET_KEY-in-env-for-production",
)

DEBUG = os.environ.get("DEBUG", "False").strip().lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "accounts",
    "workers",
    "alerts",
    "sitemap",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sitesafe.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sitesafe.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "sitesafe"),
        "USER": os.environ.get("DB_USER", "sitesafe"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

========================================================================
## FILE: backend/sitesafe/urls.py
========================================================================
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from alerts.views import AlertIngestView, AlertViewSet
from workers.views import WorkerViewSet

router = DefaultRouter()
router.register("workers", WorkerViewSet, basename="worker")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/alerts/ingest/", AlertIngestView.as_view(), name="alert-ingest"),
    path("api/", include(router.urls)),
]

========================================================================
## FILE: backend/sitesafe/wsgi.py
========================================================================
"""
WSGI config for sitesafe project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitesafe.settings')

application = get_wsgi_application()

========================================================================
## FILE: backend/workers/__init__.py
========================================================================


========================================================================
## FILE: backend/workers/admin.py
========================================================================
from django.contrib import admin

from .models import Worker


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("name", "vest_id", "zone", "is_active", "created_at")
    list_filter = ("is_active", "zone")
    search_fields = ("name", "vest_id")

========================================================================
## FILE: backend/workers/apps.py
========================================================================
from django.apps import AppConfig


class WorkersConfig(AppConfig):
    name = 'workers'

========================================================================
## FILE: backend/workers/migrations/0001_initial.py
========================================================================
# Generated by Django 6.0 on 2026-04-13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Worker",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("vest_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("zone", models.CharField(blank=True, default="", max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]

========================================================================
## FILE: backend/workers/migrations/__init__.py
========================================================================


========================================================================
## FILE: backend/workers/models.py
========================================================================
from django.db import models


class Worker(models.Model):
    name = models.CharField(max_length=255)
    vest_id = models.CharField(max_length=64, unique=True, db_index=True)
    zone = models.CharField(max_length=128, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.vest_id})"

========================================================================
## FILE: backend/workers/serializers.py
========================================================================
from rest_framework import serializers

from .models import Worker


class WorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ("id", "name", "vest_id", "zone", "is_active", "created_at")
        read_only_fields = ("id", "created_at")

========================================================================
## FILE: backend/workers/tests.py
========================================================================
from django.test import TestCase

# Create your tests here.

========================================================================
## FILE: backend/workers/views.py
========================================================================
from rest_framework import viewsets

from .models import Worker
from .serializers import WorkerSerializer


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer

========================================================================
## FILE: docs/.gitkeep
========================================================================


========================================================================
## FILE: frontend/.gitkeep
========================================================================

