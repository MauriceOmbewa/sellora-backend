"""Product selectors — all read queries."""
from django.db.models import QuerySet
from apps.products.models import Product


def get_products_for_business(business, status: str = None,
                               category_id=None, search: str = None) -> QuerySet:
    """
    Return products for a business with optional filters.
    Used by the dashboard product list.
    """
    qs = Product.objects.filter(business=business).select_related("category")
    if status:
        qs = qs.filter(status=status)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs.order_by("-created_at")


def get_storefront_products(business, category_id=None,
                            search: str = None, sort: str = None) -> QuerySet:
    """
    Return products visible on the public storefront.
    Only active + available products. costPrice excluded at serializer level.
    """
    qs = (
        Product.objects
        .filter(business=business, status="active", is_available=True)
        .select_related("category")
    )
    if category_id:
        qs = qs.filter(category_id=category_id)
    if search:
        qs = qs.filter(name__icontains=search)

    sort_map = {
        "newest": "-created_at",
        "price-asc": "selling_price",
        "price-desc": "-selling_price",
        "best-selling": "-total_sold",
        "featured": "-is_featured",
    }
    qs = qs.order_by(sort_map.get(sort, "-is_featured"))
    return qs


def get_product_by_id(product_id, business=None) -> Product | None:
    qs = Product.objects.filter(id=product_id).select_related("category", "business")
    if business:
        qs = qs.filter(business=business)
    return qs.first()


def get_product_by_slug(slug: str, business) -> Product | None:
    return (
        Product.objects
        .filter(slug=slug, business=business, status="active", is_available=True)
        .select_related("category")
        .first()
    )


def get_low_stock_products(business) -> QuerySet:
    """Return products at or below their low_stock_threshold."""
    from django.db.models import F
    return (
        Product.objects
        .filter(business=business, status="active")
        .filter(stock_quantity__lte=F("low_stock_threshold"))
        .order_by("stock_quantity")
    )


def product_slug_exists(slug: str, business, exclude_id=None) -> bool:
    qs = Product.objects.filter(slug=slug, business=business)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()
