"""Messages services."""
import logging
from django.db import transaction
from django.db.transaction import on_commit

from apps.messages.models import CustomerMessage

logger = logging.getLogger("apps")


@transaction.atomic
def create_message(business, *, sender_name: str, body: str,
                   sender_phone: str = "", sender_email: str = "",
                   subject: str = "", channel: str = "contact_form") -> CustomerMessage:
    """
    Create a customer inquiry message.
    Called by the public storefront contact form endpoint.
    Dispatches email notification after commit.
    """
    msg = CustomerMessage.objects.create(
        business=business,
        sender_name=sender_name,
        sender_phone=sender_phone,
        sender_email=sender_email,
        subject=subject,
        body=body,
        channel=channel,
        status="unread",
    )

    msg_id_str = str(msg.id)
    on_commit(lambda: _dispatch_new_message_alert(msg_id_str))

    logger.info(
        "Customer message created from %s for business %s",
        sender_name, business.id,
    )
    return msg


def _dispatch_new_message_alert(message_id: str):
    try:
        from apps.notifications.tasks import send_new_message_alert
        send_new_message_alert.delay(message_id)
    except Exception as exc:
        logger.warning("Failed to dispatch new message alert: %s", exc)


@transaction.atomic
def update_message_status(message: CustomerMessage, status: str) -> CustomerMessage:
    """Mark a message as read or replied."""
    message.status = status
    message.save(update_fields=["status", "updated_at"])
    return message
