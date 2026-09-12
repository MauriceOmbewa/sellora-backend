"""
Product serializers.

ProductSerializer        — full dashboard output (includes cost_price)
ProductPublicSerializer  — storefront output (NO cost_price, NO draft/archived)
ProductCreateSerializer  — POST input validation
ProductUpdateSerializer  — PATCH input validation
"""
from rest_framework import serializers

from apps.products.models import Product
from apps.products.constants import PRODUCT_STATUS_CHOICES, PRODUCT_BADGE_CHOICES
from apps.products.selectors import product_slug_exists


# ─── Output serializers ───────────────────────────────────────────────────────

class ProductSerializer(serializers.ModelSerializer):
    """
    Full product representation for authenticated dashboard views.
    Includes cost_price and all status values.
    """
    category_id = serializers.UUIDField(
        source="category.id", read_only=True, allow_null=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    stock_status = serializers.CharField(read_only=True)
    display_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "business",
            "category_id",
            "category_name",
            "name",
            "slug",
            "description",
            "images",
            "selling_price",
            "cost_price",
            "sale_price",
            "display_price",
            "sku",
            "stock_quantity",
            "low_stock_threshold",
            "stock_status",
            "status",
            "is_featured",
            "is_available",
            "badge",
            "tags",
            "total_sold",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProductPublicSerializer(serializers.ModelSerializer):
    """
    Storefront-safe product representation.

    Critically:
      - cost_price is EXCLUDED
      - Only active + available products reach this serializer
        (filtered at the selector level, not here)
    """
    category_id = serializers.UUIDField(
        source="category.id", read_only=True, allow_null=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    display_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "category_id",
            "category_name",
            "name",
            "slug",
            "description",
            "images",
            "selling_price",
            "sale_price",
            "display_price",
            "stock_quantity",
            "stock_status",
            "is_featured",
            "badge",
            "tags",
            "total_sold",
            "created_at",
        ]
        read_only_fields = fields

    @property
    def stock_status(self):
        return self.instance.stock_status if self.instance else None


# ─── Input serializers ────────────────────────────────────────────────────────

class ProductCreateSerializer(serializers.Serializer):
    """Validates POST /products/ payload."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category_id = serializers.UUIDField(required=False, allow_null=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    sale_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    stock_quantity = serializers.IntegerField(required=False, default=0, min_value=0)
    low_stock_threshold = serializers.IntegerField(required=False, default=5, min_value=0)
    status = serializers.ChoiceField(choices=PRODUCT_STATUS_CHOICES, required=False, default="draft")
    is_featured = serializers.BooleanField(required=False, default=False)
    is_available = serializers.BooleanField(required=False, default=True)
    images = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )
    badge = serializers.ChoiceField(
        choices=PRODUCT_BADGE_CHOICES + [("", "None")],
        required=False, allow_blank=True, default=""
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False, default=list
    )
    slug = serializers.SlugField(max_length=100, required=False)

    def validate_selling_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Selling price must be greater than zero.")
        return value

    def validate_sale_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Sale price must be greater than zero.")
        return value


class ProductUpdateSerializer(serializers.Serializer):
    """Validates PATCH /products/{id}/ payload. All fields optional."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    selling_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    cost_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    sale_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    stock_quantity = serializers.IntegerField(required=False, min_value=0)
    low_stock_threshold = serializers.IntegerField(required=False, min_value=0)
    status = serializers.ChoiceField(choices=PRODUCT_STATUS_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)
    is_available = serializers.BooleanField(required=False)
    images = serializers.ListField(child=serializers.URLField(), required=False)
    badge = serializers.ChoiceField(
        choices=PRODUCT_BADGE_CHOICES + [("", "None")],
        required=False, allow_blank=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False
    )
    slug = serializers.SlugField(max_length=100, required=False)

    def validate_slug(self, value):
        business = self.context.get("business")
        product = self.context.get("product")
        exclude_id = product.id if product else None
        if product_slug_exists(value, business, exclude_id=exclude_id):
            raise serializers.ValidationError(
                "This slug is already used by another product in this business."
            )
        return value
