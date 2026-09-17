"""
Messages URL patterns.

Contact-form / legacy messages (business-scoped, authenticated):
  GET    /api/v1/businesses/{business_id}/messages/
  GET    /api/v1/businesses/{business_id}/messages/{message_id}/
  PATCH  /api/v1/businesses/{business_id}/messages/{message_id}/

WhatsApp conversations (business-scoped, authenticated):
  GET    /api/v1/businesses/{business_id}/whatsapp/conversations/
  GET    /api/v1/businesses/{business_id}/whatsapp/conversations/{conversation_id}/
  POST   /api/v1/businesses/{business_id}/whatsapp/conversations/{conversation_id}/reply/

WhatsApp integration settings (business-scoped, authenticated):
  GET    /api/v1/businesses/{business_id}/whatsapp/settings/
  POST   /api/v1/businesses/{business_id}/whatsapp/settings/
  DELETE /api/v1/businesses/{business_id}/whatsapp/settings/

NOTE: The webhook endpoint lives outside the business-scoped prefix at:
  /api/v1/webhooks/whatsapp/
It is registered in api/v1/urls.py (AllowAny — Meta cannot send Bearer tokens).
"""
from django.urls import path

from apps.messages.views import (
    MessageDetailView,
    MessageListView,
    WhatsAppConversationDetailView,
    WhatsAppConversationListView,
    WhatsAppReplyView,
    WhatsAppSettingsView,
    WhatsAppEmbeddedSignupView,
)

urlpatterns = [
    # ── Contact-form messages ──────────────────────────────────────────────────
    path("", MessageListView.as_view(), name="message-list"),
    path("<uuid:message_id>/", MessageDetailView.as_view(), name="message-detail"),
]

whatsapp_urlpatterns = [
    # ── WhatsApp conversations ─────────────────────────────────────────────────
    path(
        "conversations/",
        WhatsAppConversationListView.as_view(),
        name="whatsapp-conversation-list",
    ),
    path(
        "conversations/<uuid:conversation_id>/",
        WhatsAppConversationDetailView.as_view(),
        name="whatsapp-conversation-detail",
    ),
    path(
        "conversations/<uuid:conversation_id>/reply/",
        WhatsAppReplyView.as_view(),
        name="whatsapp-reply",
    ),
    # ── WhatsApp settings ──────────────────────────────────────────────────────
    path(
        "settings/",
        WhatsAppSettingsView.as_view(),
        name="whatsapp-settings",
    ),
    # ── Embedded Signup — complete connection after Meta popup ─────────────────
    path(
        "connect/",
        WhatsAppEmbeddedSignupView.as_view(),
        name="whatsapp-connect",
    ),
]
