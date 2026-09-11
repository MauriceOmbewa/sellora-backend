"""
Testing settings.
- In-memory SQLite for fast test runs
- No Celery tasks executed synchronously
- Dummy cache
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Use SQLite in-memory for speed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Run Celery tasks eagerly (synchronously) in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Silence drf-spectacular schema generation warnings in tests
import warnings  # noqa: E402
warnings.filterwarnings("ignore", module="drf_spectacular")
