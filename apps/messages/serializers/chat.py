from rest_framework import serializers

from apps.messages.models import (
    ChatConversation,
    ChatMessage,
    ChatVisitor,
)


class ChatVisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatVisitor
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "sender_type",
            "content",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sender_type",
            "is_read",
            "created_at",
        ]


class ChatConversationSerializer(serializers.ModelSerializer):
    visitor = ChatVisitorSerializer(read_only=True)

    class Meta:
        model = ChatConversation
        fields = [
            "id",
            "visitor",
            "status",
            "last_message_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "visitor",
            "status",
            "last_message_at",
            "created_at",
        ]


class ChatConversationDetailSerializer(ChatConversationSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatConversationSerializer.Meta):
        fields = ChatConversationSerializer.Meta.fields + [
            "messages",
        ]