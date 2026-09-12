from django.contrib import admin
from apps.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name", "business", "category", "selling_price",
        "stock_quantity", "status", "is_available", "is_featured", "total_sold",
    ]
    list_filter = ["status", "is_available", "is_featured", "business"]
    search_fields = ["name", "slug", "sku", "business__name"]
    readonly_fields = [
        "id", "total_sold", "stock_status", "display_price",
        "created_at", "updated_at",
    ]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ["business", "category"]
    fieldsets = (
        ("Identity", {"fields": ("id", "business", "category", "name", "slug", "description")}),
        ("Media", {"fields": ("images",)}),
        ("Pricing", {"fields": ("selling_price", "cost_price", "sale_price", "display_price")}),
        ("Inventory", {"fields": ("sku", "stock_quantity", "low_stock_threshold", "stock_status")}),
        ("Status", {"fields": ("status", "is_available", "is_featured", "badge", "tags")}),
        ("Stats", {"fields": ("total_sold",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
