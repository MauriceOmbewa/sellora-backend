from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "name", "is_staff", "is_active", "created_at"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["email", "name", "google_id"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "google_id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "name", "avatar", "google_id")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login")}),
    )

    # No add form — users are created via Google OAuth only
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name"),
        }),
    )
