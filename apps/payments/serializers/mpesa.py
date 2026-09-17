from rest_framework import serializers


class STKPushSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1
    )

    phone = serializers.CharField(
        max_length=15
    )

    account_reference = serializers.CharField(
        max_length=100,
        required=False,
        default="Sellora Payment"
    )

    transaction_description = serializers.CharField(
        max_length=255,
        required=False,
        default="Payment for Sellora order"
    )