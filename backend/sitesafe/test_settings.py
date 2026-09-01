"""Isolated settings for a fast, non-destructive local test run.

Production and development continue to use PostgreSQL through ``settings``.
This module exists so contributors and CI can exercise the API suite without
requiring permission to create or drop a PostgreSQL test database.
"""

from .settings import *  # noqa: F403


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
