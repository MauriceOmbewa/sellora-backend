from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.messages.models import ChatConversation, ChatMessage


User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"][
            "conversation_id"
        ]

        self.room_group_name = (
            f"chat_conversation_{self.conversation_id}"
        )

        conversation_exists = await self.conversation_exists()

        if not conversation_exists:
            await self.close()
            return

        self.authenticated = False
        self.sender_type = None

        await self.accept()

    async def disconnect(self, close_code):
        if self.authenticated:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        if not self.authenticated:
            if message_type != "auth":
                await self.send_json({
                    "type": "error",
                    "message": "Authentication is required.",
                })
                return

            authenticated = await self.authenticate_client(content)

            if not authenticated:
                await self.send_json({
                    "type": "error",
                    "message": "Authentication failed.",
                })
                await self.close()
                return

            self.authenticated = True

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name,
            )

            await self.send_json({
                "type": "auth.success",
                "sender_type": self.sender_type,
            })

            return

        if message_type != "message":
            await self.send_json({
                "type": "error",
                "message": "Invalid message type.",
            })
            return

        message_content = content.get("content", "").strip()

        if not message_content:
            await self.send_json({
                "type": "error",
                "message": "Message content is required.",
            })
            return

        message = await self.create_message(
            sender_type=self.sender_type,
            content=message_content,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": str(message.id),
                    "conversation_id": str(message.conversation_id),
                    "sender_type": message.sender_type,
                    "content": message.content,
                    "is_read": message.is_read,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        await self.send_json({
            "type": "chat.message",
            "message": event["message"],
        })

    async def authenticate_client(self, content):
        role = content.get("role")

        if role == "visitor":
            visitor_id = content.get("visitor_id")

            if not visitor_id:
                return False

            valid = await self.authenticate_visitor(visitor_id)

            if valid:
                self.sender_type = "visitor"

            return valid

        if role == "business":
            access_token = content.get("access_token")

            if not access_token:
                return False

            valid = await self.authenticate_business(access_token)

            if valid:
                self.sender_type = "business"

            return valid

        return False

    @database_sync_to_async
    def authenticate_visitor(self, visitor_id):
        conversation = (
            ChatConversation.objects
            .select_related("visitor")
            .filter(
                id=self.conversation_id,
                status="open",
            )
            .first()
        )

        if not conversation:
            return False

        return str(conversation.visitor_id) == str(visitor_id)

    @database_sync_to_async
    def authenticate_business(self, access_token):
        try:
            token = AccessToken(access_token)
            user_id = token["user_id"]
            user = User.objects.get(id=user_id)
        except Exception:
            return False

        return ChatConversation.objects.filter(
            id=self.conversation_id,
            status="open",
            business__owner=user,
        ).exists()

    @database_sync_to_async
    def conversation_exists(self):
        return ChatConversation.objects.filter(
            id=self.conversation_id,
            status="open",
        ).exists()

    @database_sync_to_async
    def create_message(self, sender_type, content):
        conversation = ChatConversation.objects.get(
            id=self.conversation_id,
            status="open",
        )

        message = ChatMessage.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            content=content,
        )

        conversation.last_message_at = message.created_at

        conversation.save(
            update_fields=[
                "last_message_at",
                "updated_at",
            ],
        )

        return message