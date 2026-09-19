"""
BusinessSettings serializer.
Used for GET /businesses/{id}/settings/ and PUT /businesses/{id}/settings/
"""
from rest_framework import serializers

from apps.businesses.models import BusinessSettings


class BusinessSettingsSerializer(serializers.ModelSerializer):
    """
    Serializes notification preferences, locale settings, and delivery config.
    All fields optional on update — only sent fields are changed.
    """

    class Meta:
        model = BusinessSettings
        fields = [
            "email_on_new_order",
            "email_on_low_stock",
            "email_on_new_message",
            "sms_on_new_order",
            "currency",
            "timezone",
            "language",
            # Delivery
            "delivery_enabled",
            "pickup_enabled",
            "delivery_fee",
            "free_delivery_threshold",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
