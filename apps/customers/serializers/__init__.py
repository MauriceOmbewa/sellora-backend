from rest_framework import serializers
from apps.customers.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "name", "phone", "email", "location",
            "total_orders", "total_spent",
            "last_purchase_at", "first_purchase_at",
            "status", "notes", "tags", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CustomerUpdateSerializer(serializers.Serializer):
    """Dashboard can update notes, tags, status only."""
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False
    )
    status = serializers.ChoiceField(
        choices=[("active", "Active"), ("inactive", "Inactive")], required=False
    )
    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
