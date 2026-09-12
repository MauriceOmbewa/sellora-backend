from django.contrib import admin
from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "name", "phone", "email", "business",
        "total_orders", "total_spent", "status", "created_at",
    ]
    list_filter = ["status", "business"]
    search_fields = ["name", "phone", "email"]
    readonly_fields = [
        "id", "total_orders", "total_spent",
        "last_purchase_at", "first_purchase_at",
        "created_at", "updated_at",
    ]
    raw_id_fields = ["business"]
