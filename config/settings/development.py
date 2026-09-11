"""
Development settings.
- DEBUG on
- Detailed error pages
- Console email backend
- No HTTPS enforcement
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Allow all origins in dev — tighten in production
CORS_ALLOW_ALL_ORIGINS = True

# ─── Dev-only apps ────────────────────────────────────────────────────────────
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]

MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

# ─── Simpler password hashing in dev (faster tests) ──────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ─── Email goes to console in dev ─────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Disable cache in dev (use dummy cache so behavior is explicit) ───────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
