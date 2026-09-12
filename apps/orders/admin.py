from django.contrib import admin
from apps.orders.models import Order, OrderItem, OrderTimeline


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["id", "product", "product_name", "sku",
                       "quantity", "unit_price", "total_price"]
    can_delete = False


class OrderTimelineInline(admin.TabularInline):
    model = OrderTimeline
    extra = 0
    readonly_fields = ["status", "note", "timestamp"]
    can_delete = False
    ordering = ["timestamp"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "business", "customer_name", "customer_phone",
        "total", "status", "payment_status", "channel", "created_at",
    ]
    list_filter = ["status", "payment_status", "channel", "business"]
    search_fields = ["order_number", "customer_name", "customer_phone"]
    readonly_fields = [
        "id", "order_number", "subtotal", "total",
        "created_at", "updated_at",
    ]
    raw_id_fields = ["business", "customer"]
    inlines = [OrderItemInline, OrderTimelineInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product_name", "sku", "quantity", "unit_price", "total_price"]
    search_fields = ["product_name", "sku", "order__order_number"]
    readonly_fields = ["id", "total_price", "created_at", "updated_at"]


@admin.register(OrderTimeline)
class OrderTimelineAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "note", "timestamp"]
    readonly_fields = ["order", "status", "note", "timestamp"]
