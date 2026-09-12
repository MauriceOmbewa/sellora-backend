"""
Business serializers.

Three distinct serializers with distinct responsibilities:

  BusinessCreateSerializer  — validates the onboarding POST payload
  BusinessUpdateSerializer  — validates partial updates (PATCH)
  BusinessSerializer        — shapes the full output for GET responses
"""
from rest_framework import serializers

from apps.businesses.models import Business
from apps.businesses.selectors import business_slug_exists
from apps.businesses.validators import validate_slug, validate_theme
from apps.businesses.constants import (
    BUSINESS_CATEGORY_CHOICES,
    BUSINESS_STATUS_CHOICES,
    BUSINESS_PLAN_CHOICES,
)


# ─── Nested output serializers ────────────────────────────────────────────────

class ThemeSerializer(serializers.Serializer):
    primaryColor = serializers.CharField(max_length=7, required=False)
    primaryHover = serializers.CharField(max_length=7, required=False)
    accentColor = serializers.CharField(max_length=7, required=False)
    backgroundColor = serializers.CharField(max_length=7, required=False)
    textColor = serializers.CharField(max_length=7, required=False)

    def validate(self, data):
        validate_theme(data)
        return data


class ContactSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    whatsapp = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    openingHours = serializers.CharField(max_length=255, required=False, allow_blank=True)


class SocialLinksSerializer(serializers.Serializer):
    instagram = serializers.URLField(required=False, allow_blank=True)
    facebook = serializers.URLField(required=False, allow_blank=True)
    tiktok = serializers.URLField(required=False, allow_blank=True)
    twitter = serializers.URLField(required=False, allow_blank=True)
    youtube = serializers.URLField(required=False, allow_blank=True)


class HeroSerializer(serializers.Serializer):
    heading = serializers.CharField(max_length=255, required=False, allow_blank=True)
    subheading = serializers.CharField(max_length=500, required=False, allow_blank=True)
    ctaText = serializers.CharField(max_length=100, required=False, allow_blank=True)
    ctaSecondaryText = serializers.CharField(max_length=100, required=False, allow_blank=True)
    imageUrl = serializers.URLField(required=False, allow_blank=True)


# ─── Output serializer ────────────────────────────────────────────────────────

class BusinessSerializer(serializers.ModelSerializer):
    """
    Full business representation returned by GET endpoints.

    Nested JSON fields are returned as structured objects, not raw dicts,
    so the frontend gets predictable shapes.

    Read-only — never used for input validation.
    """
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    # Expose computed storefront publish state for convenience
    is_storefront_published = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "owner_id",
            "owner_name",
            "owner_email",
            "name",
            "slug",
            "category",
            "description",
            "motto",
            "logo",
            "favicon",
            "status",
            "plan",
            "theme",
            "contact",
            "social_links",
            "hero",
            "about_text",
            "total_products",
            "total_orders",
            "total_customers",
            "total_revenue",
            "is_storefront_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_storefront_published(self, obj) -> bool:
        try:
            return obj.storefront_settings.is_published
        except Exception:
            return False


# ─── Create serializer (onboarding) ──────────────────────────────────────────

class BusinessCreateSerializer(serializers.Serializer):
    """
    Validates the 4-step onboarding payload.

    The frontend sends one combined POST with all steps merged:
        Step 1 — name, category, description, motto
        Step 2 — logo (URL from upload endpoint), contact info
        Step 3 — theme customisation
        Step 4 — hero content
    """
    # Step 1
    name = serializers.CharField(max_length=255)
    category = serializers.ChoiceField(choices=BUSINESS_CATEGORY_CHOICES)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    motto = serializers.CharField(max_length=255, required=False, allow_blank=True)

    # Step 2
    logo = serializers.URLField(required=False, allow_blank=True)
    contact = ContactSerializer(required=False)

    # Step 3
    theme = ThemeSerializer(required=False)

    # Step 4
    hero = HeroSerializer(required=False)
    about_text = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Business name must be at least 2 characters.")
        return value.strip()


# ─── Update serializer (settings page) ───────────────────────────────────────

class BusinessUpdateSerializer(serializers.Serializer):
    """
    Validates partial updates to a Business (PATCH /businesses/{id}/).

    Every field is optional — only supplied fields are updated.
    Slug updates are validated for uniqueness against other businesses.
    """
    name = serializers.CharField(max_length=255, required=False)
    slug = serializers.CharField(max_length=100, required=False)
    category = serializers.ChoiceField(choices=BUSINESS_CATEGORY_CHOICES, required=False)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    motto = serializers.CharField(max_length=255, required=False, allow_blank=True)
    logo = serializers.URLField(required=False, allow_blank=True)
    favicon = serializers.URLField(required=False, allow_blank=True)
    contact = ContactSerializer(required=False)
    theme = ThemeSerializer(required=False)
    social_links = SocialLinksSerializer(required=False)
    hero = HeroSerializer(required=False)
    about_text = serializers.CharField(required=False, allow_blank=True)

    def validate_slug(self, value):
        validate_slug(value)
        # Check uniqueness — context["business"] is injected by the view
        business = self.context.get("business")
        exclude_id = business.id if business else None
        if business_slug_exists(value, exclude_id=exclude_id):
            raise serializers.ValidationError(
                "This slug is already taken. Please choose a different one."
            )
        return value

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Business name must be at least 2 characters.")
        return value.strip()
