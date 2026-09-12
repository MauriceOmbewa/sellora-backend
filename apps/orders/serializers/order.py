"""Order serializers."""
from rest_framework import serializers

from apps.orders.models import Order, OrderItem, OrderTimeline
from apps.orders.constants import (
    ORDER_STATUS_CHOICES,
    ORDER_STATUS_TRANSITIONS,
    PAYMENT_METHOD_CHOICES,
    ORDER_CHANNEL_CHOICES,
    PAYMENT_STATUS_CHOICES,
)


class OrderTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTimeline
        fields = ["status", "note", "timestamp"]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "product_name", "product_image",
            "sku", "quantity", "unit_price", "total_price",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Full order output including nested items and timeline."""
    items = OrderItemSerializer(many=True, read_only=True)
    timeline = OrderTimelineSerializer(many=True, read_only=True)
    next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "business",
            "customer", "customer_name", "customer_phone",
            "customer_email", "delivery_address", "order_notes",
            "subtotal", "delivery_fee", "discount", "total",
            "status", "payment_status", "payment_method", "channel",
            "next_statuses",
            "items", "timeline",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_next_statuses(self, obj) -> list:
        """Return valid next statuses for the frontend to render action buttons."""
        return ORDER_STATUS_TRANSITIONS.get(obj.status, [])


class OrderItemInputSerializer(serializers.Serializer):
    """Validates a single line item in an order creation request."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    """
    Validates POST /orders/ (dashboard) and POST /store/:slug/orders/ (storefront).
    Used for both channels — all fields validated here; business logic in service.
    """
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=30)
    customer_email = serializers.EmailField(required=False, allow_blank=True, default="")
    delivery_address = serializers.CharField(required=False, allow_blank=True, default="")
    order_notes = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, default="cash"
    )
    channel = serializers.ChoiceField(
        choices=ORDER_CHANNEL_CHOICES, default="online"
    )
    items = serializers.ListField(
        child=OrderItemInputSerializer(),
        min_length=1,
        error_messages={"min_length": "Order must contain at least one item."},
    )
    discount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, default=0, min_value=0,
    )

    def validate_customer_phone(self, value):
        value = value.strip().replace(" ", "")
        if len(value) < 9:
            raise serializers.ValidationError("Phone number is too short.")
        return value


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Validates PATCH /orders/{id}/status/"""
    status = serializers.ChoiceField(choices=ORDER_STATUS_CHOICES)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        order = self.context.get("order")
        if order:
            allowed = ORDER_STATUS_TRANSITIONS.get(order.status, [])
            if data["status"] not in allowed:
                raise serializers.ValidationError({
                    "status": (
                        f"Cannot transition from '{order.status}' to '{data['status']}'. "
                        f"Allowed transitions: {allowed or ['none — terminal state']}."
                    )
                })
        return data


class OrderPaymentStatusSerializer(serializers.Serializer):
    """Validates PATCH /orders/{id}/payment-status/"""
    payment_status = serializers.ChoiceField(choices=PAYMENT_STATUS_CHOICES)
