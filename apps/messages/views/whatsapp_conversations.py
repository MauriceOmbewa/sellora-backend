"""
WhatsApp conversation + settings dashboard views.

All routes are business-scoped (require IsAuthenticated + IsBusinessOwner).

Conversation routes:
  GET  /businesses/{id}/whatsapp/conversations/
  GET  /businesses/{id}/whatsapp/conversations/{conv_id}/
  POST /businesses/{id}/whatsapp/conversations/{conv_id}/reply/

WhatsApp integration settings:
  GET    /businesses/{id}/whatsapp/settings/
  POST   /businesses/{id}/whatsapp/settings/
  DELETE /businesses/{id}/whatsapp/settings/
"""
import logging

import requests as http_requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.messages.selectors.whatsapp import (
    get_conversation_by_id,
    get_conversations_for_business,
    get_messages_for_conversation,
)
from apps.messages.serializers.whatsapp import (
    WhatsAppConversationDetailSerializer,
    WhatsAppConversationSerializer,
    WhatsAppReplySerializer,
    WhatsAppSettingsReadSerializer,
    WhatsAppSettingsSerializer,
)
from apps.messages.services.whatsapp import (
    disconnect_whatsapp,
    get_whatsapp_settings,
    save_whatsapp_settings,
    send_whatsapp_message,
)
from common.exceptions import ResourceNotFound, ValidationError
from common.pagination import StandardResultsPagination
from common.responses import created_response, no_content_response, success_response

logger = logging.getLogger("apps")


# ─────────────────────────────────────────────────────────────────────────────
# Conversation list
# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppConversationListView(APIView):
    """
    GET /businesses/{business_id}/whatsapp/conversations/
    Query params: status=open|closed|awaiting_reply
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        conversations = get_conversations_for_business(
            request.business,
            status=request.query_params.get("status"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(conversations, request)
        return paginator.get_paginated_response(
            WhatsAppConversationSerializer(page, many=True).data
        )


# ─────────────────────────────────────────────────────────────────────────────
# Conversation detail
# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppConversationDetailView(APIView):
    """
    GET /businesses/{business_id}/whatsapp/conversations/{conversation_id}/

    Returns the conversation + full message thread.
    Also resets unread_count to 0 when opened.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_or_404(self, conversation_id, business):
        conv = get_conversation_by_id(conversation_id, business=business)
        if not conv:
            raise ResourceNotFound("Conversation not found.")
        return conv

    def get(self, request, business_id, conversation_id):
        conv = self._get_or_404(conversation_id, request.business)

        # Reset unread badge when employee opens the conversation
        if conv.unread_count > 0:
            from apps.messages.models import WhatsAppConversation
            WhatsAppConversation.objects.filter(pk=conv.pk).update(unread_count=0)
            conv.unread_count = 0

        # Prefetch messages for the serializer
        conv._prefetched_messages = get_messages_for_conversation(conv)

        return success_response(
            data=WhatsAppConversationDetailSerializer(conv).data
        )


# ─────────────────────────────────────────────────────────────────────────────
# Reply
# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppReplyView(APIView):
    """
    POST /businesses/{business_id}/whatsapp/conversations/{conversation_id}/reply/
    Body: { "body": "Your message text" }

    Sends a WhatsApp message to the customer via Meta Cloud API.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id, conversation_id):
        conv = get_conversation_by_id(conversation_id, business=request.business)
        if not conv:
            raise ResourceNotFound("Conversation not found.")

        serializer = WhatsAppReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = send_whatsapp_message(
                conversation=conv,
                body=serializer.validated_data["body"],
                sent_by=request.user,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        except http_requests.HTTPError as exc:
            logger.error("Meta API error on reply: %s", exc)
            raise ValidationError(
                "Failed to send message via WhatsApp. Please check your API credentials."
            )

        from apps.messages.serializers.whatsapp import WhatsAppMessageSerializer
        return created_response(
            data=WhatsAppMessageSerializer(message).data,
            message="Message sent.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp integration settings
# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppSettingsView(APIView):
    """
    GET    /businesses/{business_id}/whatsapp/settings/
    POST   /businesses/{business_id}/whatsapp/settings/
    DELETE /businesses/{business_id}/whatsapp/settings/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        wa_settings = get_whatsapp_settings(request.business)
        if not wa_settings:
            return success_response(data=None)
        return success_response(
            data=WhatsAppSettingsReadSerializer(wa_settings).data
        )

    def post(self, request, business_id):
        serializer = WhatsAppSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        wa_settings = save_whatsapp_settings(
            business=request.business,
            phone_number=d["phone_number"],
            phone_number_id=d["phone_number_id"],
            waba_id=d["waba_id"],
            access_token=d["access_token"],
            webhook_verify_token=d["webhook_verify_token"],
        )

        return created_response(
            data=WhatsAppSettingsReadSerializer(wa_settings).data,
            message="WhatsApp integration connected.",
        )

    def delete(self, request, business_id):
        disconnect_whatsapp(request.business)
        return no_content_response()
