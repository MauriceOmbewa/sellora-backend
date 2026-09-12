"""
Business services — all write operations for the businesses domain.

Rules:
  - Services are the only layer that creates, updates, or deletes data.
  - Services call selectors for reads; never write raw ORM queries in views.
  - All DB operations that span multiple models use atomic transactions.
"""
import logging
from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business, BusinessSettings, StorefrontSettings
from apps.businesses.utils import generate_unique_slug
from apps.businesses.constants import DEFAULT_HERO

logger = logging.getLogger("apps")


@transaction.atomic
def create_business(owner, *, name: str, category: str, description: str = "",
                    motto: str = "", logo: str = "", slug: str = None,
                    contact: dict = None, theme: dict = None,
                    social_links: dict = None, hero: dict = None,
                    about_text: str = "") -> Business:
    """
    Create a new Business and its companion Settings records.

    Called by the onboarding flow (4-step wizard on the frontend).

    Auto-generates a unique slug from the business name if one is not
    supplied. The onboarding form does not ask the user for a slug — it
    is derived automatically.

    Also initialises:
      - BusinessSettings with sensible defaults
      - StorefrontSettings (unpublished by default)

    Args:
        owner:       The User who owns this business.
        name:        Business display name.
        category:    One of BUSINESS_CATEGORY_CHOICES keys.
        description: Short description.
        motto:       Tagline / motto.
        logo:        URL to the uploaded logo image.
        slug:        Optional explicit slug. Auto-generated if not provided.
        contact:     Dict with phone, whatsapp, email, address, city, country,
                     openingHours. Missing keys are filled with defaults.
        theme:       Dict with primaryColor, primaryHover, accentColor,
                     backgroundColor, textColor.
        social_links: Dict with instagram, facebook, tiktok, twitter, youtube.
        hero:        Dict with heading, subheading, ctaText, ctaSecondaryText,
                     imageUrl.
        about_text:  Long-form about section text.

    Returns:
        The newly created Business instance (with settings already attached).
    """
    # ── Slug ──────────────────────────────────────────────────────────────────
    final_slug = slug if slug else generate_unique_slug(name)

    # ── Hero defaults (mirror the onboarding page behaviour) ─────────────────
    final_hero = DEFAULT_HERO.copy()
    if hero:
        final_hero.update(hero)
    if not final_hero.get("heading"):
        final_hero["heading"] = f"Welcome to {name}"
    if not final_hero.get("subheading"):
        final_hero["subheading"] = motto or description

    # ── Create the Business ───────────────────────────────────────────────────
    business = Business.objects.create(
        owner=owner,
        name=name,
        slug=final_slug,
        category=category,
        description=description,
        motto=motto,
        logo=logo,
        plan="starter",
        status="active",
        contact=contact or {},
        theme=theme or {},
        social_links=social_links or {},
        hero=final_hero,
        about_text=about_text,
    )

    # ── Create companion settings (auto via signal, but also here for safety) -
    BusinessSettings.objects.get_or_create(business=business)
    StorefrontSettings.objects.get_or_create(business=business)

    logger.info("Business created: %s (slug=%s) by user %s", name, final_slug, owner.id)
    return business


@transaction.atomic
def update_business(business: Business, **fields) -> Business:
    """
    Update editable fields on a Business.

    JSON fields (theme, contact, social_links, hero) are deep-merged with
    existing values so the caller only needs to send changed keys.

    Args:
        business: The Business instance to update.
        **fields: Any subset of Business field names → new values.

    Returns:
        The updated Business instance.
    """
    json_fields = {"theme", "contact", "social_links", "hero"}
    update_fields = []

    for field, value in fields.items():
        if field in json_fields and isinstance(value, dict):
            # Merge: keep existing keys, overwrite with provided ones
            current = getattr(business, field) or {}
            current.update(value)
            setattr(business, field, current)
        else:
            setattr(business, field, value)
        update_fields.append(field)

    # If name changed and no explicit slug was provided, regenerate slug
    if "name" in fields and "slug" not in fields:
        business.slug = generate_unique_slug(business.name, exclude_id=business.id)
        update_fields.append("slug")

    update_fields.append("updated_at")
    business.save(update_fields=update_fields)
    return business


@transaction.atomic
def update_business_settings(business: Business, **fields) -> BusinessSettings:
    """
    Update BusinessSettings for a business.

    Args:
        business: The owning Business.
        **fields: Any subset of BusinessSettings field names → new values.

    Returns:
        The updated BusinessSettings instance.
    """
    settings, _ = BusinessSettings.objects.get_or_create(business=business)

    for field, value in fields.items():
        setattr(settings, field, value)

    settings.save(update_fields=list(fields.keys()) + ["updated_at"])
    return settings


@transaction.atomic
def update_storefront_settings(business: Business, **fields) -> StorefrontSettings:
    """
    Save storefront configuration changes (without publishing).

    The publish action is a separate explicit step so the owner can
    stage changes and preview before going live.

    Args:
        business: The owning Business.
        **fields: Any subset of StorefrontSettings field names → new values.

    Returns:
        The updated StorefrontSettings instance.
    """
    sf_settings, _ = StorefrontSettings.objects.get_or_create(business=business)

    for field, value in fields.items():
        setattr(sf_settings, field, value)

    sf_settings.save(update_fields=list(fields.keys()) + ["updated_at"])
    return sf_settings


@transaction.atomic
def publish_storefront(business: Business) -> StorefrontSettings:
    """
    Publish the storefront, making it visible to the public.

    Sets is_published=True and records the publish timestamp.
    The business must have status='active' to be published.

    Args:
        business: The Business whose storefront to publish.

    Returns:
        The updated StorefrontSettings instance.

    Raises:
        ValueError if the business is not active.
    """
    if business.status != "active":
        raise ValueError("Only active businesses can publish their storefront.")

    sf_settings, _ = StorefrontSettings.objects.get_or_create(business=business)
    sf_settings.is_published = True
    sf_settings.last_published_at = timezone.now()
    sf_settings.save(update_fields=["is_published", "last_published_at", "updated_at"])

    logger.info("Storefront published for business %s (slug=%s)", business.id, business.slug)
    return sf_settings


@transaction.atomic
def unpublish_storefront(business: Business) -> StorefrontSettings:
    """
    Take the storefront offline.

    Args:
        business: The Business whose storefront to unpublish.

    Returns:
        The updated StorefrontSettings instance.
    """
    sf_settings, _ = StorefrontSettings.objects.get_or_create(business=business)
    sf_settings.is_published = False
    sf_settings.save(update_fields=["is_published", "updated_at"])

    logger.info("Storefront unpublished for business %s", business.id)
    return sf_settings
