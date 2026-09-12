"""
CustomerMessage — inquiries submitted via the storefront contact form
or other channels (WhatsApp, email).

Not related to Django's messages framework (which uses label 'messages').
This app uses label 'customer_messages' (set in apps.py).
"""
from django.db import models
from apps.core.models import BaseModel

MESSAGE_CHANNEL_CHOICES = [
    ("contact_form", "Contact Form"),
    ("whatsapp", "WhatsApp"),
    ("email", "Email"),
]

MESSAGE_STATUS_CHOICES = [
    ("unread", "Unread"),
    ("read", "Read"),
    ("replied", "Replied"),
]


class CustomerMessage(BaseModel):

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )

    sender_name = models.CharField(max_length=255)
    sender_phone = models.CharField(max_length=30, blank=True, default="")
    sender_email = models.EmailField(blank=True, default="")
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField()

    channel = models.CharField(
        max_length=20,
        choices=MESSAGE_CHANNEL_CHOICES,
        default="contact_form",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=MESSAGE_STATUS_CHOICES,
        default="unread",
        db_index=True,
    )

    class Meta:
        app_label = "customer_messages"
        db_table = "messages_customer_message"
        verbose_name = "Customer Message"
        verbose_name_plural = "Customer Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
        ]

    def __str__(self):
        return f"Message from {self.sender_name} ({self.status})"
