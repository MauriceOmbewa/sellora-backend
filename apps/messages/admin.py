from django.contrib import admin
from apps.messages.models import CustomerMessage


@admin.register(CustomerMessage)
class CustomerMessageAdmin(admin.ModelAdmin):
    list_display = [
        "sender_name", "sender_phone", "sender_email",
        "business", "channel", "status", "created_at",
    ]
    list_filter = ["status", "channel", "business"]
    search_fields = ["sender_name", "sender_phone", "sender_email", "body"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business"]

    def has_add_permission(self, request):
        return False  # Messages come from the storefront only
