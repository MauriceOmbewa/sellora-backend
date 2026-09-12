"""
factory_boy factories for all domain models.

Usage:
    from tests.factories import UserFactory, BusinessFactory, ProductFactory

    user = UserFactory()
    business = BusinessFactory(owner=user)
    product = ProductFactory(business=business)
"""
import uuid
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker()


# ── Accounts ──────────────────────────────────────────────────────────────────

class UserFactory(DjangoModelFactory):
    class Meta:
        model = "accounts.User"

    id = factory.LazyFunction(uuid.uuid4)
    google_id = factory.LazyFunction(lambda: fake.uuid4())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    name = factory.LazyAttribute(lambda _: fake.name())
    avatar = factory.LazyAttribute(lambda _: fake.image_url())
    is_active = True
    is_staff = False


# ── Businesses ────────────────────────────────────────────────────────────────

class BusinessFactory(DjangoModelFactory):
    class Meta:
        model = "businesses.Business"

    id = factory.LazyFunction(uuid.uuid4)
    owner = factory.SubFactory(UserFactory)
    name = factory.LazyAttribute(lambda _: fake.company())
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-")[:50])
    category = "cosmetics"
    description = factory.LazyAttribute(lambda _: fake.sentence())
    motto = factory.LazyAttribute(lambda _: fake.catch_phrase())
    status = "active"
    plan = "starter"


class BusinessSettingsFactory(DjangoModelFactory):
    class Meta:
        model = "businesses.BusinessSettings"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    email_on_new_order = True
    email_on_low_stock = True
    email_on_new_message = True
    sms_on_new_order = False
    currency = "KES"
    timezone = "Africa/Nairobi"


class StorefrontSettingsFactory(DjangoModelFactory):
    class Meta:
        model = "businesses.StorefrontSettings"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    is_published = True


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = "categories.Category"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    name = factory.LazyAttribute(lambda _: fake.word().capitalize())
    slug = factory.LazyAttribute(lambda o: o.name.lower())
    is_active = True
    sort_order = 0


# ── Products ──────────────────────────────────────────────────────────────────

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = "products.Product"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    category = factory.SubFactory(CategoryFactory, business=factory.SelfAttribute("..business"))
    name = factory.LazyAttribute(lambda _: fake.catch_phrase())
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-")[:80])
    description = factory.LazyAttribute(lambda _: fake.paragraph())
    selling_price = factory.LazyAttribute(lambda _: Decimal(str(fake.random_int(500, 10000))))
    cost_price = factory.LazyAttribute(lambda o: o.selling_price * Decimal("0.4"))
    sku = factory.LazyAttribute(lambda _: fake.bothify("??-####"))
    stock_quantity = 100
    low_stock_threshold = 5
    status = "active"
    is_available = True
    is_featured = False


# ── Customers ─────────────────────────────────────────────────────────────────

class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = "customers.Customer"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    name = factory.LazyAttribute(lambda _: fake.name())
    phone = factory.LazyAttribute(lambda _: f"+254{fake.msisdn()[3:12]}")
    email = factory.LazyAttribute(lambda _: fake.email())
    status = "active"


# ── Orders ────────────────────────────────────────────────────────────────────

class OrderFactory(DjangoModelFactory):
    class Meta:
        model = "orders.Order"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    customer = factory.SubFactory(CustomerFactory, business=factory.SelfAttribute("..business"))
    order_number = factory.Sequence(lambda n: f"#{1001 + n}")
    customer_name = factory.LazyAttribute(lambda o: o.customer.name)
    customer_phone = factory.LazyAttribute(lambda o: o.customer.phone)
    customer_email = factory.LazyAttribute(lambda o: o.customer.email)
    subtotal = Decimal("3000.00")
    delivery_fee = Decimal("300.00")
    discount = Decimal("0.00")
    total = Decimal("3300.00")
    status = "new"
    payment_status = "pending"
    payment_method = "mpesa"
    channel = "online"


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = "orders.OrderItem"

    id = factory.LazyFunction(uuid.uuid4)
    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    product_name = factory.LazyAttribute(lambda o: o.product.name)
    sku = factory.LazyAttribute(lambda o: o.product.sku)
    quantity = 2
    unit_price = Decimal("1500.00")
    total_price = Decimal("3000.00")


# ── Finances ──────────────────────────────────────────────────────────────────

class ExpenseFactory(DjangoModelFactory):
    class Meta:
        model = "finances.Expense"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    category = "stock_purchases"
    description = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    amount = factory.LazyAttribute(lambda _: Decimal(str(fake.random_int(1000, 20000))))
    date = factory.LazyAttribute(lambda _: fake.date_this_month())


# ── Messages ──────────────────────────────────────────────────────────────────

class CustomerMessageFactory(DjangoModelFactory):
    class Meta:
        model = "customer_messages.CustomerMessage"

    id = factory.LazyFunction(uuid.uuid4)
    business = factory.SubFactory(BusinessFactory)
    sender_name = factory.LazyAttribute(lambda _: fake.name())
    sender_phone = factory.LazyAttribute(lambda _: f"+254{fake.msisdn()[3:12]}")
    sender_email = factory.LazyAttribute(lambda _: fake.email())
    body = factory.LazyAttribute(lambda _: fake.paragraph())
    channel = "contact_form"
    status = "unread"
