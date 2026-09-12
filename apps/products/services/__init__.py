"""Product services — all write operations."""
import logging
from django.db import transaction
from django.utils.text import slugify

from apps.products.models import Product
from apps.products.selectors import product_slug_exists

logger = logging.getLogger("apps")


def _generate_product_slug(name: str, business, exclude_id=None) -> str:
    base = slugify(name)[:90]
    slug = base
    counter = 2
    while product_slug_exists(slug, business, exclude_id=exclude_id):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_product(business, *, name: str, selling_price,
                   category=None, description: str = "",
                   cost_price=0, sale_price=None,
                   sku: str = "", stock_quantity: int = 0,
                   low_stock_threshold: int = 5,
                   status: str = "draft",
                   is_featured: bool = False,
                   is_available: bool = True,
                   images: list = None,
                   badge: str = "", tags: list = None,
                   slug: str = None) -> Product:
    """Create a new Product for a business."""
    final_slug = slug or _generate_product_slug(name, business)
    product = Product.objects.create(
        business=business,
        category=category,
        name=name,
        slug=final_slug,
        description=description,
        selling_price=selling_price,
        cost_price=cost_price,
        sale_price=sale_price,
        sku=sku,
        stock_quantity=stock_quantity,
        low_stock_threshold=low_stock_threshold,
        status=status,
        is_featured=is_featured,
        is_available=is_available,
        images=images or [],
        badge=badge,
        tags=tags or [],
    )
    logger.info("Product created: %s (id=%s) for business %s",
                name, product.id, business.id)
    return product


@transaction.atomic
def update_product(product: Product, **fields) -> Product:
    """
    Update a Product. Re-slugs if name changes without explicit slug.
    images and tags are replaced entirely (not merged) on update.
    """
    update_fields = []
    for field, value in fields.items():
        setattr(product, field, value)
        update_fields.append(field)

    if "name" in fields and "slug" not in fields:
        product.slug = _generate_product_slug(
            product.name, product.business, exclude_id=product.id
        )
        update_fields.append("slug")

    update_fields.append("updated_at")
    product.save(update_fields=update_fields)
    return product


@transaction.atomic
def adjust_stock(product: Product, quantity_delta: int, reason: str = "") -> Product:
    """
    Adjust product stock quantity. Creates a StockAdjustment audit record.

    Args:
        product:        The Product to adjust.
        quantity_delta: Signed integer. Positive = add, negative = remove.
        reason:         Human-readable reason for the adjustment.

    Returns:
        The updated Product.

    Raises:
        ValueError if adjustment would make stock negative.
    """
    from apps.inventory.services import create_stock_adjustment

    new_quantity = product.stock_quantity + quantity_delta
    if new_quantity < 0:
        raise ValueError(
            f"Adjustment of {quantity_delta} would result in negative stock "
            f"({product.stock_quantity} + {quantity_delta} = {new_quantity})."
        )

    previous = product.stock_quantity
    product.stock_quantity = new_quantity
    product.save(update_fields=["stock_quantity", "updated_at"])

    # Create audit record
    create_stock_adjustment(
        product=product,
        quantity_delta=quantity_delta,
        previous_stock=previous,
        new_stock=new_quantity,
        reason=reason,
    )

    logger.info(
        "Stock adjusted for product %s: %d → %d (delta=%d, reason=%s)",
        product.id, previous, new_quantity, quantity_delta, reason,
    )
    return product


@transaction.atomic
def archive_product(product: Product) -> Product:
    """Set product status to archived."""
    product.status = "archived"
    product.is_available = False
    product.save(update_fields=["status", "is_available", "updated_at"])
    return product
