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
    "daphne",
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
    "reports",
    "channels",
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
# Site time zone, used where the server writes times into text (alert
# descriptions, emails). Stored timestamps are always UTC.
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
# Overridable so a measurement or test stack keeps its files apart.
MEDIA_ROOT = Path(os.environ["MEDIA_ROOT"]) if os.environ.get("MEDIA_ROOT") else BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "accounts.service_auth.ServiceTokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    # Short-lived access tokens; the dashboard renews them with the refresh
    # token, so a leaked access token stops working quickly.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "30"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")

ASGI_APPLICATION = "sitesafe.asgi.application"

# The in-memory layer only reaches websocket clients served by the same
# process. Set REDIS_URL when running more than one ASGI process (or the MQTT
# consumer as its own process) so broadcasts reach every client.
REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# Holds each camera's latest live-view frame. Shared through Redis when the
# API runs as several processes; in-process otherwise.
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Live view (Cameras page). Cameras post their annotated frame a few times a
# second; the API relays it to Safety Officers and Admins over /ws/cameras/
# and keeps only the latest frame per camera in memory, never on disk.
LIVE_VIEW_ENABLED = os.environ.get("LIVE_VIEW_ENABLED", "True").strip().lower() in ("1", "true", "yes")
LIVE_FRAME_MAX_BYTES = 256 * 1024
LIVE_FRAME_MAX_SIDE = 1920
LIVE_MAX_FPS = 15
# A camera with no frame for this long is shown as offline.
LIVE_OFFLINE_AFTER_SECONDS = 5

# Email notifications. Defaults to printing to the console so development
# never sends real mail; configure an SMTP backend through the environment.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").strip().lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "sitesafe@localhost")

# A vest that has not reported for this long is shown as offline.
VEST_OFFLINE_AFTER_SECONDS = int(os.environ.get("VEST_OFFLINE_AFTER_SECONDS", "120"))

# Camera-based location. A badge sighting places a worker in the camera's
# zone for this long (cameras report sightings every 15 s); after that they
# are "last seen" there and the presence monitor records the zone exit.
CAMERA_PRESENCE_SECONDS = int(os.environ.get("CAMERA_PRESENCE_SECONDS", "60"))
# A camera's people count stops counting towards its zone after this long.
CAMERA_COUNT_STALE_SECONDS = int(os.environ.get("CAMERA_COUNT_STALE_SECONDS", "30"))
# Head counts are noisy (a person flickering in and out of detection), so an
# over-capacity alert needs the zone over its limit this long, and the next
# one needs it back within the limit this long first.
ZONE_CAPACITY_CONFIRM_SECONDS = int(os.environ.get("ZONE_CAPACITY_CONFIRM_SECONDS", "10"))
ZONE_CAPACITY_CLEAR_SECONDS = int(os.environ.get("ZONE_CAPACITY_CLEAR_SECONDS", "60"))

# A worker's check-in session closes after this long without a vest report
# or QR sighting, dated to when they were last seen.
CHECKOUT_AFTER_MINUTES = int(os.environ.get("CHECKOUT_AFTER_MINUTES", "30"))

# Alert evidence (FR-29). Cameras send a JPEG of the frame that confirmed an
# alert; it is stored under MEDIA_ROOT/alert_snapshots/ and served only to
# signed-in users through /api/alerts/<id>/snapshot/. Set
# ALERT_SNAPSHOTS_ENABLED=False to discard incoming images (the model version
# and confidence are still kept). purge_alert_snapshots deletes images older
# than ALERT_SNAPSHOT_RETENTION_DAYS; schedule it daily.
ALERT_SNAPSHOTS_ENABLED = os.environ.get("ALERT_SNAPSHOTS_ENABLED", "True").strip().lower() in ("1", "true", "yes")
ALERT_SNAPSHOT_RETENTION_DAYS = int(os.environ.get("ALERT_SNAPSHOT_RETENTION_DAYS", "30"))
ALERT_SNAPSHOT_MAX_BYTES = int(os.environ.get("ALERT_SNAPSHOT_MAX_BYTES", str(512 * 1024)))
ALERT_SNAPSHOT_MAX_SIDE = 4096

REPORT_SERVICE_URL = os.environ.get(
    "REPORT_SERVICE_URL",
    "http://localhost:3001/generate",
)
REPORT_SERVICE_TIMEOUT = int(os.environ.get("REPORT_SERVICE_TIMEOUT", "120"))
