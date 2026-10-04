
from django.db import models

from apps.core.models import BaseModel


CHAT_MESSAGE_SENDER_CHOICES = [
    ("visitor", "Visitor"),
    ("business", "Business"),
]


class ChatMessage(BaseModel):
    """
    A single message sent within a live chat conversation.
    """

    conversation = models.ForeignKey(
        "customer_messages.ChatConversation",
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )

    sender_type = models.CharField(
        max_length=20,
        choices=CHAT_MESSAGE_SENDER_CHOICES,
    )

    content = models.TextField()

    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        db_table = "messages_chat_message"
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
        ]

    def __str__(self):
        return f"{self.sender_type} message in {self.conversation_id}"
