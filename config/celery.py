"""
Celery application configuration for Sellora.

All background tasks (order notifications, low-stock alerts, etc.)
are registered here via autodiscovery from each app's tasks.py.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("sellora")

# Read config from Django settings, namespace all Celery keys with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
