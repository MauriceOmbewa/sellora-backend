"""
BusinessSettings — per-business operational configuration.

1:1 with Business. Created automatically via signal when a Business is created.
"""
from django.db import models

from apps.core.models import BaseModel


class BusinessSettings(BaseModel):
    """
    Notification preferences and locale settings for a business.

    Accessed at:  GET/PUT /api/v1/businesses/{id}/settings/
    """

    business = models.OneToOneField(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="settings",
        primary_key=False,
    )

    # ── Notification preferences ──────────────────────────────────────────────
    email_on_new_order = models.BooleanField(default=True)
    email_on_low_stock = models.BooleanField(default=True)
    email_on_new_message = models.BooleanField(default=True)
    sms_on_new_order = models.BooleanField(default=False)

    # ── Locale ────────────────────────────────────────────────────────────────
    currency = models.CharField(max_length=10, default="KES")
    timezone = models.CharField(max_length=50, default="Africa/Nairobi")
    language = models.CharField(max_length=10, default="en")

    class Meta:
        db_table = "businesses_settings"
        verbose_name = "Business Settings"
        verbose_name_plural = "Business Settings"

    def __str__(self):
        return f"Settings for {self.business.name}"
