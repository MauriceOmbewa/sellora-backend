"""
WhatsApp Cloud API webhook endpoint.

GET  /api/v1/webhooks/whatsapp/
     Meta calls this once during setup to verify the endpoint.
     Must echo back the hub.challenge value.

POST /api/v1/webhooks/whatsapp/
     Meta calls this for every inbound message and delivery status update.
     Payload is matched to a business via the phone_number_id in metadata.

Both endpoints are public (no JWT auth) — Meta cannot send Bearer tokens.
Security is provided by:
  - GET:  matching hub.verify_token against each business's stored token
  - POST: HMAC-SHA256 signature in X-Hub-Signature-256 header (WHATSAPP_APP_SECRET)
"""
import json
import logging

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import WhatsAppSettings
from apps.messages.services.whatsapp import (
    process_inbound_webhook,
    verify_webhook_signature,
)

logger = logging.getLogger("apps")


class WhatsAppWebhookView(APIView):
    """
    Handles both the verification challenge (GET) and live events (POST)
    from Meta's WhatsApp Business Platform.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    # ── GET — hub verification ────────────────────────────────────────────────
    def get(self, request):
        """
        Meta sends this when you first register (or update) the webhook URL.
        Params: hub.mode, hub.verify_token, hub.challenge
        We look up the business whose webhook_verify_token matches hub.verify_token
        and echo back hub.challenge as plain text.
        """
        mode         = request.query_params.get("hub.mode")
        verify_token = request.query_params.get("hub.verify_token")
        challenge    = request.query_params.get("hub.challenge")

        if mode != "subscribe" or not verify_token or not challenge:
            logger.warning("WhatsApp webhook GET: missing required params")
            return HttpResponse("Bad Request", status=400)

        # Find the business whose stored token matches
        match = WhatsAppSettings.objects.filter(
            webhook_verify_token=verify_token,
            is_active=True,
        ).first()

        if not match:
            logger.warning(
                "WhatsApp webhook GET: no matching verify_token '%s'", verify_token
            )
            return HttpResponse("Forbidden", status=403)

        logger.info(
            "WhatsApp webhook verified for business %s", match.business_id
        )
        # Must return the challenge as plain text with status 200
        return HttpResponse(challenge, content_type="text/plain", status=200)

    # ── POST — inbound events ─────────────────────────────────────────────────
    def post(self, request):
        """
        Meta POSTs every inbound message and delivery-status update here.
        We verify the HMAC signature, identify the business from the
        phone_number_id in the payload, then hand off to the service layer.
        Always return 200 immediately — Meta retries on anything else.
        """
        raw_body = request.body
        signature = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")

        if not verify_webhook_signature(raw_body, signature):
            logger.warning("WhatsApp webhook POST: invalid HMAC signature")
            # Still return 200 to stop Meta from retrying (it's an invalid request)
            return Response({"status": "ok"}, status=200)

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError):
            logger.warning("WhatsApp webhook POST: malformed JSON body")
            return Response({"status": "ok"}, status=200)

        if payload.get("object") != "whatsapp_business_account":
            # Ignore non-WhatsApp events (e.g. Instagram, Messenger)
            return Response({"status": "ok"}, status=200)

        # Extract phone_number_id from the first change to identify the business
        phone_number_id = None
        try:
            phone_number_id = (
                payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            )
        except (KeyError, IndexError, TypeError):
            logger.warning("WhatsApp webhook POST: could not extract phone_number_id")
            return Response({"status": "ok"}, status=200)

        # Look up which business owns this phone_number_id
        wa_settings = WhatsAppSettings.objects.select_related("business").filter(
            phone_number_id=phone_number_id,
            is_active=True,
        ).first()

        if not wa_settings:
            logger.warning(
                "WhatsApp webhook POST: unregistered phone_number_id '%s'",
                phone_number_id,
            )
            return Response({"status": "ok"}, status=200)

        try:
            process_inbound_webhook(payload, wa_settings.business)
        except Exception as exc:
            # Log but never raise — Meta must always get a 200 back
            logger.exception(
                "WhatsApp webhook processing error for business %s: %s",
                wa_settings.business_id, exc,
            )

        return Response({"status": "ok"}, status=200)
