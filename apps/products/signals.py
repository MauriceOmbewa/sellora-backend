"""
Product signals.

1. When a product is created → increment category.product_count +
   increment business.total_products.
2. When a product is deleted → decrement the same counters.
3. When a product's category changes → adjust both old and new category counts.
"""
import logging
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.products.models import Product

logger = logging.getLogger("apps")


@receiver(post_save, sender=Product)
def on_product_saved(sender, instance, created, **kwargs):
    if created:
        # Increment business total_products counter
        from apps.businesses.signals import increment_business_counter
        increment_business_counter(instance.business_id, "total_products", 1)

        # Increment category product_count if category is set
        if instance.category_id:
            from apps.categories.signals import increment_category_product_count
            increment_category_product_count(instance.category_id, 1)


@receiver(post_delete, sender=Product)
def on_product_deleted(sender, instance, **kwargs):
    from apps.businesses.signals import increment_business_counter
    increment_business_counter(instance.business_id, "total_products", -1)

    if instance.category_id:
        from apps.categories.signals import increment_category_product_count
        increment_category_product_count(instance.category_id, -1)


@receiver(pre_save, sender=Product)
def on_product_category_changed(sender, instance, **kwargs):
    """
    Detect category changes on update and adjust category product counts.
    Uses the database state (pre-save) vs the new value (instance).
    """
    if not instance.pk:
        return  # new product — handled by post_save

    try:
        old = Product.objects.only("category_id").get(pk=instance.pk)
    except Product.DoesNotExist:
        return

    old_cat_id = old.category_id
    new_cat_id = instance.category_id

    if old_cat_id != new_cat_id:
        from apps.categories.signals import increment_category_product_count
        if old_cat_id:
            increment_category_product_count(old_cat_id, -1)
        if new_cat_id:
            increment_category_product_count(new_cat_id, 1)
