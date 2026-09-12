"""Tests for order services — the most complex domain."""
import pytest
from decimal import Decimal
from tests.factories import BusinessFactory, ProductFactory, CustomerFactory


@pytest.mark.django_db
class TestCreateOrder:

    def test_create_order_basic(self):
        from apps.orders.services import create_order
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1500"), status="active")
        order = create_order(
            biz,
            customer_name="Jane Doe",
            customer_phone="+254712345678",
            payment_method="mpesa",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 2}],
        )
        assert order.id is not None
        assert order.order_number == "#1001"
        assert order.customer_name == "Jane Doe"
        assert order.subtotal == Decimal("3000")
        assert order.delivery_fee == Decimal("300")
        assert order.total == Decimal("3300")
        assert order.status == "new"

    def test_create_order_decrements_stock(self):
        from apps.orders.services import create_order
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1500"), status="active")
        create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 3}],
        )
        product.refresh_from_db()
        assert product.stock_quantity == 7

    def test_create_order_upserts_customer(self):
        from apps.orders.services import create_order
        from apps.customers.models import Customer
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=20,
                                  selling_price=Decimal("500"), status="active")
        create_order(
            biz,
            customer_name="New Customer",
            customer_phone="+254799000001",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 1}],
        )
        assert Customer.objects.filter(business=biz, phone="+254799000001").exists()

    def test_create_order_fails_with_insufficient_stock(self):
        from apps.orders.services import create_order
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=2,
                                  selling_price=Decimal("1000"), status="active")
        with pytest.raises(ValueError, match="Insufficient stock"):
            create_order(
                biz,
                customer_name="Jane",
                customer_phone="+254712345678",
                payment_method="cash",
                channel="online",
                items=[{"product_id": str(product.id), "quantity": 5}],
            )

    def test_free_delivery_above_threshold(self):
        from apps.orders.services import create_order
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=5,
                                  selling_price=Decimal("6000"), status="active")
        order = create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="mpesa",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 2}],
        )
        assert order.delivery_fee == Decimal("0")
        assert order.subtotal == Decimal("12000")

    def test_walk_in_has_no_delivery_fee(self):
        from apps.orders.services import create_order
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("500"), status="active")
        order = create_order(
            biz,
            customer_name="Walk-in",
            customer_phone="+254700000001",
            payment_method="cash",
            channel="walk-in",
            items=[{"product_id": str(product.id), "quantity": 1}],
        )
        assert order.delivery_fee == Decimal("0")


@pytest.mark.django_db
class TestUpdateOrderStatus:

    def test_valid_transition(self):
        from apps.orders.services import create_order, update_order_status
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1000"), status="active")
        order = create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 1}],
        )
        order = update_order_status(order, "confirmed")
        assert order.status == "confirmed"

    def test_invalid_transition_raises(self):
        from apps.orders.services import create_order, update_order_status
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1000"), status="active")
        order = create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 1}],
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            update_order_status(order, "completed")  # must go new→confirmed→... first

    def test_cancellation_restores_stock(self):
        from apps.orders.services import create_order, update_order_status
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1000"), status="active")
        order = create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 3}],
        )
        product.refresh_from_db()
        assert product.stock_quantity == 7

        update_order_status(order, "cancelled")
        product.refresh_from_db()
        assert product.stock_quantity == 10  # restored

    def test_timeline_entry_appended(self):
        from apps.orders.models import OrderTimeline
        from apps.orders.services import create_order, update_order_status
        biz = BusinessFactory()
        product = ProductFactory(business=biz, stock_quantity=10,
                                  selling_price=Decimal("1000"), status="active")
        order = create_order(
            biz,
            customer_name="Jane",
            customer_phone="+254712345678",
            payment_method="cash",
            channel="online",
            items=[{"product_id": str(product.id), "quantity": 1}],
        )
        update_order_status(order, "confirmed", note="Payment received")
        entries = OrderTimeline.objects.filter(order=order)
        assert entries.count() == 2  # initial 'new' + 'confirmed'
        assert entries.last().status == "confirmed"
        assert entries.last().note == "Payment received"
