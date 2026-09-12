"""Messages selectors."""
from django.db.models import QuerySet
from apps.messages.models import CustomerMessage


def get_messages_for_business(business, status: str = None) -> QuerySet:
    qs = CustomerMessage.objects.filter(business=business)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_message_by_id(message_id, business=None) -> CustomerMessage | None:
    qs = CustomerMessage.objects.filter(id=message_id)
    if business:
        qs = qs.filter(business=business)
    return qs.first()


def get_unread_count(business) -> int:
    return CustomerMessage.objects.filter(
        business=business, status="unread"
    ).count()
