from rest_framework import serializers
from apps.categories.models import Category
from apps.categories.selectors import category_slug_exists


class CategorySerializer(serializers.ModelSerializer):
    """Full read-only output for a category."""
    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description", "image_url",
            "product_count", "is_active", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CategoryCreateSerializer(serializers.Serializer):
    """Validates POST /categories/ payload."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    image_url = serializers.URLField(required=False, allow_blank=True, default="")
    slug = serializers.SlugField(max_length=100, required=False)
    is_active = serializers.BooleanField(required=False, default=True)
    sort_order = serializers.IntegerField(required=False, default=0, min_value=0)

    def validate(self, data):
        business = self.context["business"]
        slug = data.get("slug") or ""
        if slug and category_slug_exists(slug, business):
            raise serializers.ValidationError(
                {"slug": "This slug is already used by another category in this business."}
            )
        return data


class CategoryUpdateSerializer(serializers.Serializer):
    """Validates PATCH /categories/{id}/ payload. All fields optional."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.URLField(required=False, allow_blank=True)
    slug = serializers.SlugField(max_length=100, required=False)
    is_active = serializers.BooleanField(required=False)
    sort_order = serializers.IntegerField(required=False, min_value=0)

    def validate_slug(self, value):
        business = self.context["business"]
        category = self.context.get("category")
        exclude_id = category.id if category else None
        if category_slug_exists(value, business, exclude_id=exclude_id):
            raise serializers.ValidationError(
                "This slug is already used by another category in this business."
            )
        return value
