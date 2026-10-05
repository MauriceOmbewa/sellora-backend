from django.db import models

from apps.core.models import BaseModel


CHAT_CONVERSATION_STATUS_CHOICES = [
    ("open", "Open"),
    ("closed", "Closed"),
]


class ChatConversation(BaseModel):
    """
    A live chat conversation between a storefront visitor and a business.
    """

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="chat_conversations",
        db_index=True,
    )

    visitor = models.ForeignKey(
        "customer_messages.ChatVisitor",
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=CHAT_CONVERSATION_STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        db_table = "messages_chat_conversation"
        verbose_name = "Chat Conversation"
        verbose_name_plural = "Chat Conversations"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["visitor", "status"]),
        ]

    def __str__(self):
        return f"Conversation {self.id}"
