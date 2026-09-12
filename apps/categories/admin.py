from django.contrib import admin
from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name", "business", "slug", "product_count",
        "is_active", "sort_order", "created_at",
    ]
    list_filter = ["is_active", "business"]
    search_fields = ["name", "slug", "business__name"]
    readonly_fields = ["id", "product_count", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["business", "sort_order", "name"]
