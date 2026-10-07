from django.db.models import Prefetch

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.storefront_utils import StorefrontBusinessMixin
from apps.messages.models import (
    ChatConversation,
    ChatMessage,
    ChatVisitor,
)
from apps.messages.serializers.chat import (
    ChatConversationDetailSerializer,
    ChatConversationSerializer,
    ChatMessageSerializer,
    ChatVisitorSerializer,
)
from common.exceptions import ResourceNotFound
from common.responses import created_response, success_response


class ChatVisitorView(StorefrontBusinessMixin, APIView):
    """
    POST /api/v1/store/{slug}/chat/visitor/

    Creates a temporary visitor identity.

    If visitor_id is supplied and belongs to this storefront,
    the existing visitor is returned.
    """

    permission_classes = [AllowAny]

    def post(self, request, slug):
        business = self.storefront_business

        visitor_id = request.data.get("visitor_id")

        if visitor_id:
            try:
                visitor = ChatVisitor.objects.get(
                    id=visitor_id,
                    business=business,
                )
                return success_response(
                    data=ChatVisitorSerializer(visitor).data
                )
            except (ChatVisitor.DoesNotExist, ValueError):
                pass

        visitor = ChatVisitor.objects.create(
            business=business,
            name=request.data.get("name", ""),
            email=request.data.get("email", ""),
            phone=request.data.get("phone", ""),
        )

        return created_response(
            data=ChatVisitorSerializer(visitor).data,
            message="Chat visitor created.",
        )


class ChatConversationView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/chat/conversation/

    Returns the visitor's current open conversation.

    POST /api/v1/store/{slug}/chat/conversation/

    Creates or returns the visitor's current open conversation.
    """

    permission_classes = [AllowAny]

    def get_visitor(self, request, business):
        visitor_id = request.query_params.get("visitor_id")

        if not visitor_id:
            return None

        try:
            return ChatVisitor.objects.get(
                id=visitor_id,
                business=business,
            )
        except (ChatVisitor.DoesNotExist, ValueError):
            return None

    def get(self, request, slug):
        business = self.storefront_business
        visitor = self.get_visitor(request, business)

        if not visitor:
            return success_response(data=None)

        conversation = (
            ChatConversation.objects
            .filter(
                business=business,
                visitor=visitor,
                status="open",
            )
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=ChatMessage.objects.order_by("created_at"),
                )
            )
            .first()
        )

        if not conversation:
            return success_response(data=None)

        return success_response(
            data=ChatConversationDetailSerializer(conversation).data
        )

    def post(self, request, slug):
        business = self.storefront_business

        visitor_id = request.data.get("visitor_id")

        if not visitor_id:
            raise ValidationError({
                "visitor_id": "visitor_id is required."
            })

        try:
            visitor = ChatVisitor.objects.get(
                id=visitor_id,
                business=business,
            )
        except (ChatVisitor.DoesNotExist, ValueError):
            raise ResourceNotFound("Chat visitor not found.")

        conversation = (
            ChatConversation.objects
            .filter(
                business=business,
                visitor=visitor,
                status="open",
            )
            .first()
        )

        if conversation:
            return success_response(
                data=ChatConversationSerializer(conversation).data
            )

        conversation = ChatConversation.objects.create(
            business=business,
            visitor=visitor,
        )

        return created_response(
            data=ChatConversationSerializer(conversation).data,
            message="Chat conversation created.",
        )


class ChatConversationMessagesView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/chat/conversation/{conversation_id}/messages/

    Returns all messages belonging to the visitor's conversation.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug, conversation_id):
        business = self.storefront_business
        visitor_id = request.query_params.get("visitor_id")

        if not visitor_id:
            raise ValidationError({
                "visitor_id": "visitor_id is required."
            })

        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id,
                business=business,
                visitor_id=visitor_id,
            )
        except (ChatConversation.DoesNotExist, ValueError):
            raise ResourceNotFound("Conversation not found.")

        messages = conversation.messages.order_by("created_at")

        return success_response(
            data=ChatMessageSerializer(
                messages,
                many=True,
            ).data
        )


class BusinessChatConversationListView(APIView):
    """
    GET /api/v1/businesses/{business_id}/chat/conversations/

    Returns the conversations belonging to the authenticated
    business owner. Each conversation includes unread_count
    so the frontend can show badge counts without fetching messages.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.businesses.models import Business

        try:
            business = Business.objects.get(
                id=business_id,
                owner=request.user,
            )
        except Business.DoesNotExist:
            raise ResourceNotFound("Business not found.")

        conversations = (
            ChatConversation.objects
            .filter(business=business)
            .select_related("visitor")
            .prefetch_related("messages")   # needed for unread_count SerializerMethodField
            .order_by("-last_message_at", "-created_at")
        )

        return success_response(
            data=ChatConversationSerializer(conversations, many=True).data
        )


class BusinessChatMarkReadView(APIView):
    """
    POST /api/v1/businesses/{business_id}/chat/conversations/{conversation_id}/read/

    Marks all unread visitor messages in the conversation as read.
    Called when the business admin opens a conversation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, conversation_id):
        from apps.businesses.models import Business

        try:
            business = Business.objects.get(id=business_id, owner=request.user)
        except Business.DoesNotExist:
            raise ResourceNotFound("Business not found.")

        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id,
                business=business,
            )
        except ChatConversation.DoesNotExist:
            raise ResourceNotFound("Conversation not found.")

        updated = ChatMessage.objects.filter(
            conversation=conversation,
            sender_type="visitor",
            is_read=False,
        ).update(is_read=True)

        return success_response(data={"marked_read": updated})


class BusinessChatConversationDetailView(APIView):
    """
    GET /api/v1/businesses/{business_id}/chat/conversations/{conversation_id}/

    Returns a conversation and its messages for the business owner.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, conversation_id):
        from apps.businesses.models import Business

        try:
            business = Business.objects.get(
                id=business_id,
                owner=request.user,
            )
        except Business.DoesNotExist:
            raise ResourceNotFound("Business not found.")

        try:
            conversation = (
                ChatConversation.objects
                .select_related("visitor")
                .prefetch_related(
                    Prefetch(
                        "messages",
                        queryset=ChatMessage.objects.order_by("created_at"),
                    )
                )
                .get(
                    id=conversation_id,
                    business=business,
                )
            )
        except ChatConversation.DoesNotExist:
            raise ResourceNotFound("Conversation not found.")

        return success_response(
            data=ChatConversationDetailSerializer(conversation).data
        )