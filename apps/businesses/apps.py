from django.apps import AppConfig


class BusinessesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.businesses"
    verbose_name = "Businesses"

    def ready(self):
        import apps.businesses.signals  # noqa: F401 — register signal handlers
