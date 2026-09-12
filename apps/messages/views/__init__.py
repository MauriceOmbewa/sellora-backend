"""Messages views — dashboard (authenticated)."""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.messages.selectors import get_message_by_id, get_messages_for_business
from apps.messages.serializers import CustomerMessageSerializer, MessageStatusUpdateSerializer
from apps.messages.services import update_message_status
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import success_response

logger = logging.getLogger("apps")


class MessageListView(APIView):
    """
    GET /api/v1/businesses/{business_id}/messages/
    Query params: status=unread|read|replied, page, page_size
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        messages = get_messages_for_business(
            request.business,
            status=request.query_params.get("status"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(messages, request)
        return paginator.get_paginated_response(
            CustomerMessageSerializer(page, many=True).data
        )


class MessageDetailView(APIView):
    """
    GET   /api/v1/businesses/{business_id}/messages/{message_id}/
    PATCH /api/v1/businesses/{business_id}/messages/{message_id}/
          Body: { "status": "read" | "replied" }
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_or_404(self, message_id, business):
        msg = get_message_by_id(message_id, business=business)
        if not msg:
            raise ResourceNotFound("Message not found.")
        return msg

    def get(self, request, business_id, message_id):
        msg = self._get_or_404(message_id, request.business)
        # Auto-mark as read on open
        if msg.status == "unread":
            msg = update_message_status(msg, "read")
        return success_response(data=CustomerMessageSerializer(msg).data)

    def patch(self, request, business_id, message_id):
        msg = self._get_or_404(message_id, request.business)
        serializer = MessageStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = update_message_status(msg, serializer.validated_data["status"])
        return success_response(
            data=CustomerMessageSerializer(msg).data,
            message=f"Message marked as {msg.status}."
        )
