"""
WhatsApp query helpers (selectors).
Keep all ORM queries here — views stay thin.
"""
from django.db.models import QuerySet

from apps.messages.models import WhatsAppConversation, WhatsAppMessage


def get_conversations_for_business(
    business,
    status: str = None,
) -> QuerySet:
    """All conversations for a business, newest first."""
    qs = WhatsAppConversation.objects.filter(business=business)
    if status:
        qs = qs.filter(status=status)
    return qs.select_related("assigned_to").order_by("-last_message_at")


def get_conversation_by_id(
    conversation_id,
    business=None,
) -> WhatsAppConversation | None:
    qs = WhatsAppConversation.objects.filter(id=conversation_id)
    if business:
        qs = qs.filter(business=business)
    return qs.select_related("assigned_to", "business__whatsapp_settings").first()


def get_messages_for_conversation(conversation) -> QuerySet:
    """All messages in a conversation, oldest first (chronological thread)."""
    return (
        WhatsAppMessage.objects
        .filter(conversation=conversation)
        .select_related("sent_by")
        .order_by("message_timestamp", "created_at")
    )


def get_unread_conversation_count(business) -> int:
    return WhatsAppConversation.objects.filter(
        business=business,
        unread_count__gt=0,
    ).count()
