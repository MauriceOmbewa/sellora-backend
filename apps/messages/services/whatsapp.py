"""
WhatsApp Business Cloud API — service layer.

Two responsibilities:
  1. process_inbound_webhook(payload, business)
     Called by the webhook view when Meta POSTs an inbound message or a
     delivery-status update.  Stores data, updates conversation state, and
     fires a Celery notification task.

  2. send_whatsapp_message(conversation, body, sent_by)
     Called by the reply endpoint.  POSTs the message to Meta's Graph API,
     stores it as an outbound WhatsAppMessage, and updates the conversation.

Meta Cloud API reference
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
"""
import hashlib
import hmac
import json
import logging
import requests
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import transaction
from django.db.transaction import on_commit
from django.utils import timezone as dj_timezone

from apps.messages.models import WhatsAppConversation, WhatsAppMessage

logger = logging.getLogger("apps")

# Meta Cloud API base
_GRAPH_URL = "https://graph.facebook.com/v20.0"

# ─────────────────────────────────────────────────────────────────────────────
# Signature verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header Meta attaches to every webhook POST.
    Returns True if valid, False otherwise.

    signature_header is the raw header value: "sha256=<hex_digest>"
    """
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if not app_secret:
        # If no secret configured (dev mode), skip verification
        logger.warning("WHATSAPP_APP_SECRET not set — skipping signature verification")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


# ─────────────────────────────────────────────────────────────────────────────
# Inbound webhook processing
# ─────────────────────────────────────────────────────────────────────────────

def process_inbound_webhook(payload: dict, business) -> None:
    """
    Parse Meta's webhook payload and persist incoming messages / status updates.

    Meta's webhook structure (simplified):
    {
      "object": "whatsapp_business_account",
      "entry": [{
        "changes": [{
          "value": {
            "messaging_product": "whatsapp",
            "metadata": { "phone_number_id": "..." },
            "contacts": [{ "profile": { "name": "..." }, "wa_id": "..." }],
            "messages": [{ "id": "wamid...", "type": "text", "text": {"body": "..."}, "timestamp": "..." }],
            "statuses": [{ "id": "wamid...", "status": "delivered", ... }]
          }
        }]
      }]
    }

    Both messages[] and statuses[] can appear in the same payload.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue

            # ── Status updates (delivery receipts) ──────────────────────────
            for status_event in value.get("statuses", []):
                _handle_status_update(status_event)

            # ── Inbound messages ─────────────────────────────────────────────
            contacts = {c["wa_id"]: c for c in value.get("contacts", [])}
            for msg_data in value.get("messages", []):
                _handle_inbound_message(msg_data, contacts, business)


def _handle_status_update(status_event: dict) -> None:
    """Update delivery status of an outbound message."""
    wamid = status_event.get("id")
    new_status = status_event.get("status")  # sent | delivered | read | failed

    if not wamid or not new_status:
        return

    updated = WhatsAppMessage.objects.filter(
        whatsapp_message_id=wamid
    ).update(status=new_status)

    if updated:
        logger.debug("WhatsApp message %s status → %s", wamid, new_status)


@transaction.atomic
def _handle_inbound_message(msg_data: dict, contacts: dict, business) -> None:
    """
    Persist one inbound WhatsApp message.
    Creates or updates the parent conversation.
    Fires a notification to the business owner after commit.
    """
    wamid = msg_data.get("id")
    if not wamid:
        return

    # Deduplicate — Meta may deliver the same event more than once
    if WhatsAppMessage.objects.filter(whatsapp_message_id=wamid).exists():
        logger.debug("Duplicate webhook event for wamid %s — skipping", wamid)
        return

    customer_phone = msg_data.get("from", "")
    contact_info = contacts.get(customer_phone, {})
    customer_name = contact_info.get("profile", {}).get("name", "") or customer_phone

    msg_type = msg_data.get("type", "unknown")
    body = ""
    media_id = ""
    media_mime = ""
    media_caption = ""

    if msg_type == "text":
        body = msg_data.get("text", {}).get("body", "")
    elif msg_type in ("image", "document", "audio", "video", "sticker"):
        media_block = msg_data.get(msg_type, {})
        media_id = media_block.get("id", "")
        media_mime = media_block.get("mime_type", "")
        media_caption = media_block.get("caption", "")
        body = media_caption  # show caption as preview text
    else:
        body = f"[{msg_type} message]"

    # Parse Meta's Unix timestamp
    raw_ts = msg_data.get("timestamp")
    msg_ts = (
        datetime.fromtimestamp(int(raw_ts), tz=timezone.utc) if raw_ts else dj_timezone.now()
    )

    now = dj_timezone.now()
    window_expires = now + timedelta(hours=24)

    # get_or_create the conversation; update window + last_message_at on every inbound
    conversation, _ = WhatsAppConversation.objects.get_or_create(
        business=business,
        customer_phone=customer_phone,
        defaults={
            "customer_name": customer_name,
            "status": "open",
            "service_window_expires_at": window_expires,
            "last_message_at": now,
            "unread_count": 0,
        },
    )

    # Always update name (customer may have changed it) and reset window
    WhatsAppConversation.objects.filter(pk=conversation.pk).update(
        customer_name=customer_name,
        status="open",
        service_window_expires_at=window_expires,
        last_message_at=now,
        unread_count=conversation.unread_count + 1,
    )
    conversation.refresh_from_db()

    message = WhatsAppMessage.objects.create(
        conversation=conversation,
        whatsapp_message_id=wamid,
        direction="inbound",
        message_type=msg_type if msg_type in dict(WhatsAppMessage._meta.get_field("message_type").choices) else "unknown",
        body=body,
        media_id=media_id,
        media_mime_type=media_mime,
        media_caption=media_caption,
        status="received",
        message_timestamp=msg_ts,
    )

    conv_id_str = str(conversation.id)
    on_commit(lambda: _dispatch_whatsapp_message_alert(conv_id_str))

    logger.info(
        "Inbound WhatsApp message from %s for business %s (wamid=%s)",
        customer_phone, business.id, wamid,
    )


def _dispatch_whatsapp_message_alert(conversation_id: str) -> None:
    """Fire the Celery notification task after the transaction commits."""
    try:
        from apps.messages.tasks import notify_new_whatsapp_message
        notify_new_whatsapp_message.delay(conversation_id)
    except Exception as exc:
        logger.warning("Failed to dispatch WhatsApp message alert: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Outbound send
# ─────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def send_whatsapp_message(conversation: WhatsAppConversation, body: str, sent_by) -> WhatsAppMessage:
    """
    Send a text reply from the business to the customer via Meta Cloud API.

    Raises ValueError if the business has no active WhatsApp settings.
    Raises requests.HTTPError if Meta returns a non-2xx response.
    """
    # Fetch credentials
    try:
        wa_settings = conversation.business.whatsapp_settings
    except Exception:
        raise ValueError(
            f"Business {conversation.business_id} has no WhatsApp settings configured."
        )

    if not wa_settings.is_active:
        raise ValueError("WhatsApp integration is not active for this business.")

    # Build the Meta API payload
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": conversation.customer_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body,
        },
    }

    response = requests.post(
        f"{_GRAPH_URL}/{wa_settings.phone_number_id}/messages",
        headers={
            "Authorization": f"Bearer {wa_settings.access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.error(
            "Meta API error sending to %s: %s — %s",
            conversation.customer_phone, response.status_code, response.text,
        )
        raise

    resp_data = response.json()
    wamid = resp_data.get("messages", [{}])[0].get("id", f"local_{conversation.id}")

    now = dj_timezone.now()

    message = WhatsAppMessage.objects.create(
        conversation=conversation,
        whatsapp_message_id=wamid,
        direction="outbound",
        message_type="text",
        body=body,
        status="sent",
        sent_by=sent_by,
        message_timestamp=now,
    )

    # Update conversation
    WhatsAppConversation.objects.filter(pk=conversation.pk).update(
        last_message_at=now,
        status="open",
    )

    logger.info(
        "Outbound WhatsApp message sent to %s by %s (wamid=%s)",
        conversation.customer_phone, sent_by, wamid,
    )

    return message


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp settings CRUD helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_whatsapp_settings(business, *, phone_number: str, phone_number_id: str,
                           waba_id: str, access_token: str, webhook_verify_token: str):
    """
    Create or update the WhatsAppSettings for a business and mark it active.
    Called by the settings API endpoint.
    """
    from apps.businesses.models import WhatsAppSettings

    wa_settings, created = WhatsAppSettings.objects.update_or_create(
        business=business,
        defaults={
            "phone_number": phone_number,
            "phone_number_id": phone_number_id,
            "waba_id": waba_id,
            "access_token": access_token,
            "webhook_verify_token": webhook_verify_token,
            "is_active": True,
            "connected_at": dj_timezone.now(),
        },
    )

    logger.info(
        "%s WhatsApp settings for business %s (number=%s)",
        "Created" if created else "Updated",
        business.id, phone_number,
    )

    return wa_settings


def get_whatsapp_settings(business):
    """
    Return the WhatsAppSettings for a business, or None.
    """
    from apps.businesses.models import WhatsAppSettings
    return WhatsAppSettings.objects.filter(business=business).first()


def disconnect_whatsapp(business) -> bool:
    """
    Mark the WhatsApp integration as inactive.
    Returns True if a settings record existed, False otherwise.
    """
    from apps.businesses.models import WhatsAppSettings
    updated = WhatsAppSettings.objects.filter(business=business).update(is_active=False)
    return updated > 0
