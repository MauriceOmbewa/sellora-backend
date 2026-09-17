"""
Serializers for the WhatsApp conversations API.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.messages.models import WhatsAppConversation, WhatsAppMessage


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppMessage
        fields = [
            "id",
            "whatsapp_message_id",
            "direction",
            "message_type",
            "body",
            "media_url",
            "media_mime_type",
            "media_caption",
            "status",
            "sent_by_name",
            "message_timestamp",
            "created_at",
        ]
        read_only_fields = fields

    def get_sent_by_name(self, obj) -> str:
        if obj.sent_by:
            return obj.sent_by.name or obj.sent_by.email
        return ""


class WhatsAppConversationSerializer(serializers.ModelSerializer):
    """Summary serializer used in the conversation list."""
    service_window_active = serializers.SerializerMethodField()
    service_window_seconds_left = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppConversation
        fields = [
            "id",
            "customer_phone",
            "customer_name",
            "status",
            "unread_count",
            "last_message_at",
            "last_message_preview",
            "service_window_active",
            "service_window_seconds_left",
            "service_window_expires_at",
            "assigned_to_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_service_window_active(self, obj) -> bool:
        if not obj.service_window_expires_at:
            return False
        return obj.service_window_expires_at > timezone.now()

    def get_service_window_seconds_left(self, obj) -> int:
        if not obj.service_window_expires_at:
            return 0
        delta = obj.service_window_expires_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def get_assigned_to_name(self, obj) -> str:
        if obj.assigned_to:
            return obj.assigned_to.name or obj.assigned_to.email
        return ""

    def get_last_message_preview(self, obj) -> str:
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return ""
        if last.body:
            return last.body[:80]
        if last.message_type in ("image", "video", "audio", "document", "sticker"):
            return f"[{last.message_type}]"
        return ""


class WhatsAppConversationDetailSerializer(WhatsAppConversationSerializer):
    """Detail serializer — includes full message thread."""
    messages = WhatsAppMessageSerializer(many=True, read_only=True)

    class Meta(WhatsAppConversationSerializer.Meta):
        fields = WhatsAppConversationSerializer.Meta.fields + ["messages"]


class WhatsAppReplySerializer(serializers.Serializer):
    """Validates POST /conversations/{id}/reply/"""
    body = serializers.CharField(min_length=1, max_length=4096)


class WhatsAppSettingsSerializer(serializers.Serializer):
    """
    Validates POST /businesses/{id}/whatsapp-settings/
    All five fields are required on create; on update only provided fields change.
    """
    phone_number       = serializers.CharField(max_length=20)
    phone_number_id    = serializers.CharField(max_length=50)
    waba_id            = serializers.CharField(max_length=50)
    access_token       = serializers.CharField(max_length=2048)
    webhook_verify_token = serializers.CharField(max_length=100)


class WhatsAppSettingsReadSerializer(serializers.Serializer):
    """
    Read-only representation returned after save.
    access_token is intentionally masked — never expose it to the frontend.
    """
    phone_number         = serializers.CharField()
    phone_number_id      = serializers.CharField()
    waba_id              = serializers.CharField()
    webhook_verify_token = serializers.CharField()
    is_active            = serializers.BooleanField()
    connected_at         = serializers.DateTimeField()
    # Never expose the actual token:
    access_token_hint    = serializers.SerializerMethodField()

    def get_access_token_hint(self, obj) -> str:
        """Show only the first 8 chars so the user can confirm which token is stored."""
        token = obj.access_token if hasattr(obj, "access_token") else ""
        return (token[:8] + "…") if len(token) > 8 else "***"
