"""
WhatsAppMessage — a single message inside a WhatsAppConversation.

Direction
---------
  inbound   Customer → Business (arrived via Meta webhook)
  outbound  Business → Customer (sent by an employee via our platform)

The `whatsapp_message_id` is Meta's own message ID (wamid).  It is stored
so we can:
  1. Deduplicate webhook deliveries (Meta may deliver the same event twice).
  2. Link delivery-status updates (sent → delivered → read) back to the
     correct message record.

Media
-----
When Meta delivers a media message (image, document, audio, video) the
webhook payload contains a media_id.  The actual URL is fetched separately
via the Media API and stored in `media_url`.
"""
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


MESSAGE_DIRECTION_CHOICES = [
    ("inbound",  "Inbound"),   # customer → business
    ("outbound", "Outbound"),  # business → customer
]

MESSAGE_TYPE_CHOICES = [
    ("text",     "Text"),
    ("image",    "Image"),
    ("document", "Document"),
    ("audio",    "Audio"),
    ("video",    "Video"),
    ("sticker",  "Sticker"),
    ("template", "Template"),
    ("unknown",  "Unknown"),
]

MESSAGE_STATUS_CHOICES = [
    ("pending",   "Pending"),    # outbound: queued but not yet sent to Meta
    ("sent",      "Sent"),       # outbound: accepted by Meta
    ("delivered", "Delivered"),  # outbound: delivered to customer's device
    ("read",      "Read"),       # outbound: customer opened it
    ("failed",    "Failed"),     # outbound: Meta rejected it
    ("received",  "Received"),   # inbound: arrived from customer
]


class WhatsAppMessage(BaseModel):
    """
    A single WhatsApp message within a conversation thread.
    """

    conversation = models.ForeignKey(
        "customer_messages.WhatsAppConversation",
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )

    # ── Meta identifiers ───────────────────────────────────────────────────────
    # Unique across all messages in the system.  Used for deduplication and
    # for matching delivery-status webhook events back to this record.
    whatsapp_message_id = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="Meta wamid — e.g. wamid.HBgL...",
    )

    # ── Content ────────────────────────────────────────────────────────────────
    direction = models.CharField(
        max_length=10,
        choices=MESSAGE_DIRECTION_CHOICES,
        db_index=True,
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
    )
    body = models.TextField(blank=True, default="")

    # Media fields (null when message_type == "text")
    media_id  = models.CharField(max_length=100, blank=True, default="")
    media_url = models.URLField(max_length=500, blank=True, default="")
    media_mime_type = models.CharField(max_length=100, blank=True, default="")
    media_caption   = models.CharField(max_length=1024, blank=True, default="")

    # ── Delivery status ────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=MESSAGE_STATUS_CHOICES,
        default="received",
        db_index=True,
    )

    # Which employee sent this message (null for inbound / system messages)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_whatsapp_messages",
    )

    # Timestamp from Meta payload (may differ slightly from created_at)
    message_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "customer_messages"
        db_table = "messages_whatsapp_message"
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"
        ordering = ["message_timestamp", "created_at"]

    def __str__(self):
        preview = (self.body[:50] + "…") if len(self.body) > 50 else self.body
        return f"[{self.direction}] {preview}"
