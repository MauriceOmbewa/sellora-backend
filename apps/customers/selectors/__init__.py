"""Customer selectors — all read queries."""
from django.db.models import QuerySet
from apps.customers.models import Customer


def get_customers_for_business(business, search: str = None,
                                status: str = None) -> QuerySet:
    qs = Customer.objects.filter(business=business)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            models_Q(name__icontains=search) |
            models_Q(phone__icontains=search) |
            models_Q(email__icontains=search)
        )
    return qs.order_by("-created_at")


def get_customer_by_id(customer_id, business=None) -> Customer | None:
    qs = Customer.objects.filter(id=customer_id)
    if business:
        qs = qs.filter(business=business)
    return qs.first()


def get_customer_by_phone(phone: str, business) -> Customer | None:
    """Look up a customer by phone within a business — used for upsert on order."""
    return Customer.objects.filter(phone=phone, business=business).first()


def models_Q(*args, **kwargs):
    from django.db.models import Q
    return Q(*args, **kwargs)
