from rest_framework import serializers
from apps.messages.models import (
    CustomerMessage,
    MESSAGE_CHANNEL_CHOICES,
    MESSAGE_STATUS_CHOICES,
)


class CustomerMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerMessage
        fields = [
            "id", "sender_name", "sender_phone", "sender_email",
            "subject", "body", "channel", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class MessageStatusUpdateSerializer(serializers.Serializer):
    """Validates PATCH /messages/{id}/ — only status can be updated."""
    status = serializers.ChoiceField(choices=MESSAGE_STATUS_CHOICES)


class ContactFormSerializer(serializers.Serializer):
    """
    Validates POST /store/:slug/messages/ (public contact form).
    No auth required.
    """
    sender_name = serializers.CharField(max_length=255)
    sender_phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    sender_email = serializers.EmailField(required=False, allow_blank=True, default="")
    subject = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    body = serializers.CharField(min_length=5, max_length=5000)
    channel = serializers.ChoiceField(
        choices=MESSAGE_CHANNEL_CHOICES,
        required=False,
        default="contact_form",
    )

    def validate(self, data):
        # At least one contact method is required
        if not data.get("sender_phone") and not data.get("sender_email"):
            raise serializers.ValidationError(
                "Please provide at least a phone number or email address."
            )
        return data
