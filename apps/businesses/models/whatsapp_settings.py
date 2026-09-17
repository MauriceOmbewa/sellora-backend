"""
WhatsAppSettings — Meta WhatsApp Business Cloud API credentials per business.

Each business that wants to receive/send WhatsApp messages through the platform
needs to connect their WhatsApp Business number.  The credentials stored here
come from the Meta Business Manager after the number is registered on the
Cloud API.

Fields
------
phone_number        The human-readable number e.g. "+254712345678"
phone_number_id     Meta's internal identifier for the number (used in API calls)
waba_id             WhatsApp Business Account ID
access_token        System-user token (stored plaintext — encrypt at the infra
                    level or swap for django-fernet-fields in production)
webhook_verify_token  Random string the business sets; used to verify Meta's GET
                    challenge during webhook setup
is_active           Whether the integration is live
connected_at        When the integration was first activated
"""
from django.db import models
from apps.core.models import BaseModel


class WhatsAppSettings(BaseModel):
    """
    Per-business WhatsApp Business Cloud API configuration.

    Relation: Business ←OneToOne→ WhatsAppSettings
    The record is created explicitly when the business connects their number
    (not auto-created like BusinessSettings).
    """

    business = models.OneToOneField(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="whatsapp_settings",
    )

    # ── Number identity ────────────────────────────────────────────────────────
    phone_number = models.CharField(
        max_length=20,
        help_text="E.164 format, e.g. +254712345678",
    )
    phone_number_id = models.CharField(
        max_length=50,
        help_text="Meta phone_number_id (from Business Manager)",
    )
    waba_id = models.CharField(
        max_length=50,
        help_text="WhatsApp Business Account ID",
    )

    # ── API credentials ────────────────────────────────────────────────────────
    access_token = models.TextField(
        help_text="System-user permanent token. Treat as a secret.",
    )

    # ── Webhook ────────────────────────────────────────────────────────────────
    webhook_verify_token = models.CharField(
        max_length=100,
        help_text="Random string registered in Meta App → Webhooks → Verify Token",
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=False)
    connected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "businesses_whatsapp_settings"
        verbose_name = "WhatsApp Settings"
        verbose_name_plural = "WhatsApp Settings"

    def __str__(self):
        return f"WhatsApp: {self.phone_number} ({self.business.name})"
