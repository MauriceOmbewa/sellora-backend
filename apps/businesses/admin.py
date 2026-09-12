from django.contrib import admin

from apps.businesses.models import Business, BusinessSettings, StorefrontSettings


class BusinessSettingsInline(admin.StackedInline):
    model = BusinessSettings
    extra = 0
    readonly_fields = ["id", "created_at", "updated_at"]


class StorefrontSettingsInline(admin.StackedInline):
    model = StorefrontSettings
    extra = 0
    readonly_fields = ["id", "last_published_at", "created_at", "updated_at"]


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "owner", "category", "status",
        "plan", "total_products", "total_orders", "created_at",
    ]
    list_filter = ["status", "plan", "category"]
    search_fields = ["name", "slug", "owner__email"]
    readonly_fields = [
        "id", "total_products", "total_orders",
        "total_customers", "total_revenue", "created_at", "updated_at",
    ]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BusinessSettingsInline, StorefrontSettingsInline]
    raw_id_fields = ["owner"]


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ["business", "currency", "timezone", "email_on_new_order"]
    search_fields = ["business__name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(StorefrontSettings)
class StorefrontSettingsAdmin(admin.ModelAdmin):
    list_display = ["business", "is_published", "last_published_at"]
    list_filter = ["is_published"]
    search_fields = ["business__name"]
    readonly_fields = ["id", "last_published_at", "created_at", "updated_at"]
