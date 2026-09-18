from rest_framework import serializers


class STKPushSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()

    phone = serializers.CharField(
        max_length=15
    )


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