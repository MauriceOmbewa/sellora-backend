"""Order views — dashboard (authenticated)."""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.orders.selectors import get_order_by_id, get_orders_for_business
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    OrderPaymentStatusSerializer,
)
from apps.orders.services import create_order, update_order_status
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import created_response, success_response

logger = logging.getLogger("apps")


class OrderListCreateView(APIView):
    """
    GET  /api/v1/businesses/{business_id}/orders/
    POST /api/v1/businesses/{business_id}/orders/
    Query params: status, payment_status, customer_id, search, page, page_size
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        orders = get_orders_for_business(
            request.business,
            status=request.query_params.get("status"),
            payment_status=request.query_params.get("payment_status"),
            customer_id=request.query_params.get("customer_id"),
            search=request.query_params.get("search"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(orders, request)
        return paginator.get_paginated_response(
            OrderSerializer(page, many=True).data
        )

    def post(self, request, business_id):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Dashboard orders default to walk-in unless specified
        if "channel" not in request.data:
            data["channel"] = "walk-in"

        try:
            order = create_order(
                request.business,
                customer_name=data["customer_name"],
                customer_phone=data["customer_phone"],
                customer_email=data.get("customer_email", ""),
                delivery_address=data.get("delivery_address", ""),
                order_notes=data.get("order_notes", ""),
                payment_method=data["payment_method"],
                channel=data["channel"],
                items=data["items"],
                discount=data.get("discount", 0),
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))

        return created_response(
            data=OrderSerializer(order).data,
            message="Order created."
        )


class OrderDetailView(APIView):
    """
    GET /api/v1/businesses/{business_id}/orders/{order_id}/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id, order_id):
        order = get_order_by_id(order_id, business=request.business)
        if not order:
            raise ResourceNotFound("Order not found.")
        return success_response(data=OrderSerializer(order).data)


class OrderStatusUpdateView(APIView):
    """
    PATCH /api/v1/businesses/{business_id}/orders/{order_id}/status/
    Body: { "status": "confirmed", "note": "optional note" }
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def patch(self, request, business_id, order_id):
        order = get_order_by_id(order_id, business=request.business)
        if not order:
            raise ResourceNotFound("Order not found.")

        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={"order": order},
        )
        serializer.is_valid(raise_exception=True)

        try:
            order = update_order_status(
                order,
                serializer.validated_data["status"],
                note=serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))

        return success_response(
            data=OrderSerializer(order).data,
            message=f"Order status updated to {order.status}."
        )


class OrderPaymentStatusView(APIView):
    """
    PATCH /api/v1/businesses/{business_id}/orders/{order_id}/payment-status/
    Body: { "payment_status": "paid" }
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def patch(self, request, business_id, order_id):
        order = get_order_by_id(order_id, business=request.business)
        if not order:
            raise ResourceNotFound("Order not found.")

        serializer = OrderPaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order.payment_status = serializer.validated_data["payment_status"]
        order.save(update_fields=["payment_status", "updated_at"])

        return success_response(
            data=OrderSerializer(order).data,
            message=f"Payment status updated to {order.payment_status}."
        )
