from django.contrib import admin
from apps.finances.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "category", "amount", "date", "business", "created_at"]
    list_filter = ["category", "business"]
    search_fields = ["description", "business__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "date"
    raw_id_fields = ["business"]
