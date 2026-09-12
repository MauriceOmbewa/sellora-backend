from rest_framework import serializers
from apps.products.models import Product
from apps.inventory.models import StockAdjustment


class InventoryItemSerializer(serializers.ModelSerializer):
    """
    Computed inventory view — derived from Product.
    Adds stock_status and stock_value to the product data.
    """
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    stock_status = serializers.CharField(read_only=True)
    stock_value = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "category_name",
            "stock_quantity", "low_stock_threshold",
            "stock_status", "stock_value",
            "cost_price", "selling_price",
            "updated_at",
        ]
        read_only_fields = fields

    def get_stock_value(self, obj) -> float:
        """stock_value = current_stock × cost_price"""
        return float(obj.stock_quantity * obj.cost_price)


class StockAdjustmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockAdjustment
        fields = [
            "id", "product", "product_name",
            "quantity_delta", "previous_stock", "new_stock",
            "reason", "created_at",
        ]
        read_only_fields = fields


class StockAdjustInputSerializer(serializers.Serializer):
    """Validates POST /inventory/{product_id}/adjust/"""
    product_id = serializers.UUIDField()
    quantity_delta = serializers.IntegerField(
        help_text="Positive to add stock, negative to remove."
    )
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity delta cannot be zero.")
        return value
