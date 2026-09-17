"""
WhatsAppConversation — one thread between a business and a customer.

A conversation is opened the moment a customer messages the business's
WhatsApp number.  It stays open until the business closes it manually or
it goes stale.

The 24-hour service window is tracked via `service_window_expires_at`.
When that timestamp is in the future the business can reply with free-form
text.  Once it expires, only pre-approved templates can be sent (enforced
in the frontend UI — the backend records the window but does not block sends,
allowing the business to use templates if needed).
"""
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


CONVERSATION_STATUS_CHOICES = [
    ("open",            "Open"),
    ("closed",          "Closed"),
    ("awaiting_reply",  "Awaiting Reply"),
]


class WhatsAppConversation(BaseModel):
    """
    A WhatsApp thread between a business and one customer phone number.

    Keyed on (business, customer_phone) — there can only be one active
    conversation per customer number per business at a time.
    """

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="whatsapp_conversations",
        db_index=True,
    )

    # ── Customer identity ──────────────────────────────────────────────────────
    customer_phone = models.CharField(
        max_length=20,
        help_text="E.164 format received from Meta webhook e.g. 254712345678",
    )
    customer_name = models.CharField(max_length=255, blank=True, default="")

    # ── State ──────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=CONVERSATION_STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    # Assigned employee (nullable — unassigned by default)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_whatsapp_conversations",
    )

    # ── 24-hour service window ─────────────────────────────────────────────────
    # Set to now()+24h every time a customer message arrives.
    # Null = never received an inbound message yet (shouldn't happen normally).
    service_window_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Datetime when the free-reply service window closes",
    )

    # Denormalised for fast sorting / badge display
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "customer_messages"
        db_table = "messages_whatsapp_conversation"
        verbose_name = "WhatsApp Conversation"
        verbose_name_plural = "WhatsApp Conversations"
        ordering = ["-last_message_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["business", "customer_phone"]),
        ]
        # One active thread per customer per business
        constraints = [
            models.UniqueConstraint(
                fields=["business", "customer_phone"],
                name="unique_whatsapp_conversation_per_customer",
            )
        ]

    def __str__(self):
        return f"WA {self.customer_phone} ↔ {self.business.name}"
