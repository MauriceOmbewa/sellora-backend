"""
StorefrontSettings serializer.
Used for GET/PUT /businesses/{id}/storefront/ and POST /businesses/{id}/storefront/publish/
"""
from rest_framework import serializers

from apps.businesses.models import StorefrontSettings


class StorefrontSettingsSerializer(serializers.ModelSerializer):
    """
    Serializes the storefront display configuration.

    featured_product_ids and featured_category_ids are stored as UUID arrays.
    The frontend manages the list; the backend just stores and returns it.
    """

    class Meta:
        model = StorefrontSettings
        fields = [
            "featured_product_ids",
            "featured_category_ids",
            "show_new_arrivals",
            "show_best_sellers",
            "show_testimonials",
            "is_published",
            "last_published_at",
            "updated_at",
        ]
        read_only_fields = ["is_published", "last_published_at", "updated_at"]


class StorefrontSettingsUpdateSerializer(serializers.Serializer):
    """
    Validates PUT /businesses/{id}/storefront/ payload.
    All fields optional — only supplied fields are updated.
    is_published is NOT accepted here; use the publish endpoint instead.
    """
    featured_product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
    featured_category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
    show_new_arrivals = serializers.BooleanField(required=False)
    show_best_sellers = serializers.BooleanField(required=False)
    show_testimonials = serializers.BooleanField(required=False)

    def validate_featured_product_ids(self, value):
        # Store as strings so JSON serialization is clean
        return [str(uid) for uid in value]

    def validate_featured_category_ids(self, value):
        return [str(uid) for uid in value]
