"""
Meta WhatsApp Embedded Signup — server-side completion flow.

After a business completes the Embedded Signup popup in the browser, the
JavaScript SDK returns a short-lived `code`.  This module exchanges that code
for a permanent business token, retrieves the phone number details, subscribes
our app to webhooks on the customer's WABA, and saves everything to
WhatsAppSettings — all without the business ever touching API keys.

Meta Graph API calls made here:
  1. POST /oauth/access_token          — exchange code for business token
  2. GET  /v20.0/{waba_id}/phone_numbers — resolve phone_number_id + number
  3. POST /v20.0/{waba_id}/subscribed_apps — subscribe webhook to WABA
  4. POST /v20.0/{phone_number_id}/register — register number for Cloud API

References
  https://developers.facebook.com/docs/whatsapp/embedded-signup/getting-started/
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/phone-numbers
"""
import logging
import secrets

import requests as http_requests
from django.conf import settings
from django.utils import timezone as dj_timezone

logger = logging.getLogger("apps")

_GRAPH_URL = "https://graph.facebook.com/v20.0"


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def complete_embedded_signup(business, *, code: str, waba_id: str, phone_number_id: str) -> dict:
    """
    Exchange the Embedded Signup code for a token, resolve the phone number,
    subscribe webhooks, and persist everything to WhatsAppSettings.

    Returns a dict with the saved settings data (safe to return to frontend).

    Raises ValueError with a user-friendly message on any failure.
    """
    app_id     = getattr(settings, "WHATSAPP_APP_ID", "")
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")

    if not app_id or not app_secret:
        raise ValueError(
            "WHATSAPP_APP_ID and WHATSAPP_APP_SECRET must be configured on the server."
        )

    # Step 1 — Exchange the short-lived code for a business token
    business_token = _exchange_code_for_token(code, app_id, app_secret)

    # Step 2 — Resolve the phone number (E.164 display number)
    phone_number = _get_phone_number(phone_number_id, business_token)

    # Step 3 — Subscribe our app to webhooks on this WABA
    _subscribe_webhooks(waba_id, business_token)

    # Step 4 — Register the phone number for Cloud API use
    #           (no-op if already registered; safe to call again)
    _register_phone_number(phone_number_id, business_token)

    # Step 5 — Persist everything; generate a verify token for our webhook
    verify_token = _generate_verify_token(business.id)
    wa_settings  = _save_settings(
        business=business,
        phone_number=phone_number,
        phone_number_id=phone_number_id,
        waba_id=waba_id,
        access_token=business_token,
        webhook_verify_token=verify_token,
    )

    logger.info(
        "Embedded Signup complete for business %s — number %s (waba=%s)",
        business.id, phone_number, waba_id,
    )

    return {
        "phone_number":          wa_settings.phone_number,
        "phone_number_id":       wa_settings.phone_number_id,
        "waba_id":               wa_settings.waba_id,
        "webhook_verify_token":  wa_settings.webhook_verify_token,
        "is_active":             wa_settings.is_active,
        "connected_at":          wa_settings.connected_at.isoformat() if wa_settings.connected_at else None,
        "access_token_hint":     (wa_settings.access_token[:8] + "…") if wa_settings.access_token else "***",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step implementations
# ─────────────────────────────────────────────────────────────────────────────

def _exchange_code_for_token(code: str, app_id: str, app_secret: str) -> str:
    """
    Exchange the Embedded Signup short-lived code for a business token.
    POST /oauth/access_token
    """
    resp = http_requests.post(
        "https://graph.facebook.com/oauth/access_token",
        params={
            "client_id":     app_id,
            "client_secret": app_secret,
            "code":          code,
        },
        timeout=15,
    )

    if not resp.ok:
        logger.error("Token exchange failed: %s — %s", resp.status_code, resp.text)
        raise ValueError("Failed to exchange authorisation code. The code may have expired — please try again.")

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("Meta did not return an access token. Please try the connection again.")

    return token


def _get_phone_number(phone_number_id: str, token: str) -> str:
    """
    Retrieve the display phone number for a given phone_number_id.
    GET /v20.0/{phone_number_id}?fields=display_phone_number
    """
    resp = http_requests.get(
        f"{_GRAPH_URL}/{phone_number_id}",
        params={"fields": "display_phone_number,verified_name", "access_token": token},
        timeout=15,
    )

    if not resp.ok:
        logger.warning(
            "Could not retrieve phone number for id %s: %s", phone_number_id, resp.text
        )
        # Non-fatal — we'll store the phone_number_id and an empty number;
        # the business can still receive/send messages.
        return ""

    data = resp.json()
    # Meta returns e.g. "+254 712 345 678" — strip spaces for storage
    raw = data.get("display_phone_number", "")
    return raw.replace(" ", "")


def _subscribe_webhooks(waba_id: str, token: str) -> None:
    """
    Subscribe our Meta App to webhook events on the customer's WABA.
    POST /v20.0/{waba_id}/subscribed_apps
    This makes all message events for this WABA flow to our webhook URL.
    """
    resp = http_requests.post(
        f"{_GRAPH_URL}/{waba_id}/subscribed_apps",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )

    if not resp.ok:
        logger.error(
            "Webhook subscription failed for waba %s: %s — %s",
            waba_id, resp.status_code, resp.text,
        )
        raise ValueError(
            "Connected to WhatsApp but could not subscribe to message events. "
            "Please try disconnecting and reconnecting."
        )

    logger.debug("Subscribed webhooks for WABA %s", waba_id)


def _register_phone_number(phone_number_id: str, token: str) -> None:
    """
    Register the phone number for Cloud API use.
    POST /v20.0/{phone_number_id}/register

    Safe to call multiple times — Meta returns success even if already registered.
    The pin '000000' is used when two-step verification is not set on the number.
    """
    resp = http_requests.post(
        f"{_GRAPH_URL}/{phone_number_id}/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"messaging_product": "whatsapp", "pin": "000000"},
        timeout=15,
    )

    # 400 with "already registered" is acceptable
    if not resp.ok:
        body = resp.json() if resp.content else {}
        err_code = body.get("error", {}).get("code")
        if err_code == 132001:
            # "Phone number already registered" — fine, continue
            logger.debug("Phone %s already registered for Cloud API", phone_number_id)
            return
        logger.warning(
            "Phone number registration warning for %s: %s — %s",
            phone_number_id, resp.status_code, resp.text,
        )
        # Non-fatal warning — phone may already be in use; don't block the flow


def _generate_verify_token(business_id) -> str:
    """
    Generate a unique, unpredictable verify token for this business's webhook.
    Stored in WhatsAppSettings and registered with Meta during webhook setup.
    """
    return f"sel_{secrets.token_hex(16)}"


def _save_settings(business, *, phone_number, phone_number_id,
                   waba_id, access_token, webhook_verify_token):
    """Persist or update WhatsAppSettings for the business."""
    from apps.businesses.models import WhatsAppSettings

    wa_settings, created = WhatsAppSettings.objects.update_or_create(
        business=business,
        defaults={
            "phone_number":          phone_number,
            "phone_number_id":       phone_number_id,
            "waba_id":               waba_id,
            "access_token":          access_token,
            "webhook_verify_token":  webhook_verify_token,
            "is_active":             True,
            "connected_at":          dj_timezone.now(),
        },
    )

    logger.info(
        "%s WhatsAppSettings for business %s",
        "Created" if created else "Updated", business.id,
    )

    return wa_settings
