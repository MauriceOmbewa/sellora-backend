"""
ChatConsumer — real-time live chat WebSocket handler.

Connection lifecycle:
  1. connect()       — verify conversation exists, accept the socket
  2. receive_json()  — first message must be "auth"; then "message" or "read"
  3. disconnect()    — leave channel groups

Channel groups:
  chat_conversation_{id}  — both visitor and business for this conversation
  business_{business_id}  — business-wide notifications (new messages from any
                            visitor conversation, even if admin isn't in that
                            conversation's group)

Message types received from clients:
  auth      — authenticate as visitor (visitor_id) or business (access_token)
  message   — send a chat message
  read      — mark all unread visitor messages as read (business only)

Message types sent to clients:
  auth.success           — authentication succeeded
  chat.message           — new message broadcast to both sides
  messages.read          — all messages in conversation marked read (sent to visitor)
  new_conversation_message — sent to business-wide group when visitor sends any msg
  error                  — authentication or validation failure
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.messages.models import ChatConversation, ChatMessage


User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):

    # ── Connect / Disconnect ──────────────────────────────────────────────────

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_conversation_{self.conversation_id}"
        self.business_group_name = None   # set after auth for business clients

        if not await self.conversation_exists():
            await self.close()
            return

        self.authenticated = False
        self.sender_type   = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.authenticated:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            if self.business_group_name:
                await self.channel_layer.group_discard(self.business_group_name, self.channel_name)

    # ── Receive ───────────────────────────────────────────────────────────────

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        # ── Auth phase ────────────────────────────────────────────────────────
        if not self.authenticated:
            if message_type != "auth":
                await self.send_json({"type": "error", "message": "Authentication is required."})
                return

            authenticated = await self.authenticate_client(content)
            if not authenticated:
                await self.send_json({"type": "error", "message": "Authentication failed."})
                await self.close()
                return

            self.authenticated = True
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            # Business clients also join the per-business notification group
            if self.sender_type == "business" and self.business_group_name:
                await self.channel_layer.group_add(self.business_group_name, self.channel_name)

            await self.send_json({"type": "auth.success", "sender_type": self.sender_type})
            return

        # ── Post-auth: send a message ─────────────────────────────────────────
        if message_type == "message":
            message_content = content.get("content", "").strip()
            if not message_content:
                await self.send_json({"type": "error", "message": "Message content is required."})
                return

            message, business_id = await self.create_message(
                sender_type=self.sender_type,
                content=message_content,
            )

            msg_payload = {
                "id":              str(message.id),
                "conversation_id": str(message.conversation_id),
                "sender_type":     message.sender_type,
                "content":         message.content,
                "is_read":         message.is_read,
                "created_at":      message.created_at.isoformat(),
            }

            # Broadcast to the conversation room (both visitor + business if open)
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat_message", "message": msg_payload},
            )

            # Also notify the business-wide group so the admin sees new messages
            # from conversations they don't currently have open
            if self.sender_type == "visitor" and business_id:
                await self.channel_layer.group_send(
                    f"business_{business_id}",
                    {
                        "type":            "new_conversation_message",
                        "conversation_id": str(message.conversation_id),
                        "message":         msg_payload,
                    },
                )
            return

        # ── Post-auth: mark conversation messages as read (business only) ─────
        if message_type == "read":
            if self.sender_type != "business":
                await self.send_json({"type": "error", "message": "Only business can mark messages as read."})
                return

            await self.mark_messages_read()

            # Tell the visitor their messages were read
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "messages_read", "conversation_id": str(self.conversation_id)},
            )
            return

        await self.send_json({"type": "error", "message": "Invalid message type."})

    # ── Group event handlers ──────────────────────────────────────────────────

    async def chat_message(self, event):
        """Relay a chat message to this WebSocket connection."""
        await self.send_json({"type": "chat.message", "message": event["message"]})

    async def new_conversation_message(self, event):
        """
        Relay a new-message notification to the business-wide group.
        Only sent when visitor sends a message, so admins know a conversation
        needs attention even if they aren't viewing it.
        """
        await self.send_json({
            "type":            "new_conversation_message",
            "conversation_id": event["conversation_id"],
            "message":         event["message"],
        })

    async def messages_read(self, event):
        """Tell the visitor their messages have been read by the business."""
        await self.send_json({
            "type":            "messages.read",
            "conversation_id": event["conversation_id"],
        })

    # ── Authentication ────────────────────────────────────────────────────────

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
            .filter(id=self.conversation_id, status="open")
            .first()
        )
        if not conversation:
            return False
        return str(conversation.visitor_id) == str(visitor_id)

    @database_sync_to_async
    def authenticate_business(self, access_token):
        try:
            token   = AccessToken(access_token)
            user_id = token["user_id"]
            user    = User.objects.get(id=user_id)
        except Exception:
            return False

        conversation = ChatConversation.objects.filter(
            id=self.conversation_id,
            status="open",
            business__owner=user,
        ).select_related("business").first()

        if not conversation:
            return False

        # Store the business group name so we join it after auth
        self.business_group_name = f"business_{conversation.business_id}"
        return True

    # ── Database helpers ──────────────────────────────────────────────────────

    @database_sync_to_async
    def conversation_exists(self):
        return ChatConversation.objects.filter(id=self.conversation_id, status="open").exists()

    @database_sync_to_async
    def create_message(self, sender_type, content):
        """Create and persist a ChatMessage. Returns (message, business_id)."""
        conversation = (
            ChatConversation.objects
            .select_related("business")
            .get(id=self.conversation_id, status="open")
        )
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            content=content,
        )
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=["last_message_at", "updated_at"])
        return message, str(conversation.business_id)

    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all unread visitor messages in this conversation as read."""
        ChatMessage.objects.filter(
            conversation_id=self.conversation_id,
            sender_type="visitor",
            is_read=False,
        ).update(is_read=True)
