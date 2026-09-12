from django.contrib import admin
from apps.inventory.models import StockAdjustment


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        "product", "quantity_delta", "previous_stock",
        "new_stock", "reason", "created_at",
    ]
    list_filter = ["product__business"]
    search_fields = ["product__name", "reason"]
    readonly_fields = [
        "id", "product", "quantity_delta", "previous_stock",
        "new_stock", "reason", "created_at", "updated_at",
    ]

    def has_add_permission(self, request):
        return False  # Only created via the adjust endpoint

    def has_change_permission(self, request, obj=None):
        return False  # Immutable audit log
