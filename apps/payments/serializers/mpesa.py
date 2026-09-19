from decimal import Decimal
from rest_framework import serializers


class STKInitiateSerializer(serializers.Serializer):
    """
    Validates POST /api/v1/payments/mpesa/initiate/

    The frontend sends the full cart + customer details here BEFORE
    an order is created. The backend stores everything as a cart
    snapshot on the MpesaTransaction and only creates the real order
    once the payment callback confirms success.
    """

    # ── Business to charge ───────────────────────────────────────────
    business_slug = serializers.SlugField()

    # ── Customer ──────────────────────────────────────────────────────
    customer_name  = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=30)
    customer_email = serializers.EmailField(required=False, allow_blank=True, default="")

    # ── Delivery ──────────────────────────────────────────────────────
    delivery_address = serializers.CharField(required=False, allow_blank=True, default="")
    order_notes      = serializers.CharField(required=False, allow_blank=True, default="")
    fulfillment_type = serializers.ChoiceField(
        choices=["delivery", "pickup"], default="delivery"
    )

    # ── Cart items ────────────────────────────────────────────────────
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        error_messages={"min_length": "Cart must contain at least one item."},
    )

    # ── Optional discount ─────────────────────────────────────────────
    discount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, default=Decimal("0"), min_value=Decimal("0"),
    )

    def validate_customer_phone(self, value):
        value = value.strip().replace(" ", "")
        if len(value) < 9:
            raise serializers.ValidationError("Phone number is too short.")
        return value

    def validate_items(self, value):
        for item in value:
            if "product_id" not in item:
                raise serializers.ValidationError(
                    "Each item must include a 'product_id'."
                )
            if "quantity" not in item:
                raise serializers.ValidationError(
                    "Each item must include a 'quantity'."
                )
            try:
                qty = int(item["quantity"])
                if qty < 1:
                    raise serializers.ValidationError("Quantity must be at least 1.")
            except (ValueError, TypeError):
                raise serializers.ValidationError("'quantity' must be an integer.")
        return value


class STKPushSerializer(serializers.Serializer):
    """Legacy serializer kept for backward compatibility."""
    order_id = serializers.UUIDField()
    phone = serializers.CharField(max_length=15)


class PochiPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    phone = serializers.CharField()
    remarks = serializers.CharField(
        required=False,
        default="Sellora Payment",
    )
    occasion = serializers.CharField(
        required=False,
        default="Sellora Order",
    )
