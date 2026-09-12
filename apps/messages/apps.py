from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messages"
    label = "customer_messages"  # avoids clash with django.contrib.messages
    verbose_name = "Customer Messages"
