"""Category services — all write operations."""
import logging
from django.db import transaction
from django.utils.text import slugify

from apps.categories.models import Category
from apps.categories.selectors import category_slug_exists

logger = logging.getLogger("apps")


def _generate_category_slug(name: str, business, exclude_id=None) -> str:
    base = slugify(name)[:90]
    slug = base
    counter = 2
    while category_slug_exists(slug, business, exclude_id=exclude_id):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_category(business, *, name: str, description: str = "",
                    image_url: str = "", slug: str = None,
                    is_active: bool = True, sort_order: int = 0) -> Category:
    """Create a new Category for a business."""
    final_slug = slug or _generate_category_slug(name, business)
    category = Category.objects.create(
        business=business,
        name=name,
        slug=final_slug,
        description=description,
        image_url=image_url,
        is_active=is_active,
        sort_order=sort_order,
    )
    logger.info("Category created: %s for business %s", name, business.id)
    return category


@transaction.atomic
def update_category(category: Category, **fields) -> Category:
    """Update a Category. Re-slugs if name changes and no explicit slug given."""
    update_fields = []
    for field, value in fields.items():
        setattr(category, field, value)
        update_fields.append(field)

    if "name" in fields and "slug" not in fields:
        category.slug = _generate_category_slug(
            category.name, category.business, exclude_id=category.id
        )
        update_fields.append("slug")

    update_fields.append("updated_at")
    category.save(update_fields=update_fields)
    return category


@transaction.atomic
def delete_category(category: Category) -> None:
    """
    Delete a Category.
    Products in this category are NOT deleted — their category FK is set to NULL.
    This matches the frontend confirmation: "Products won't be deleted."
    The Product model must have category = ForeignKey(..., null=True, on_delete=SET_NULL).
    """
    logger.info("Category deleted: %s (id=%s)", category.name, category.id)
    category.delete()
