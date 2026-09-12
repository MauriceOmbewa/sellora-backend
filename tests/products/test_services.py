"""Tests for product services."""
import pytest
from decimal import Decimal
from tests.factories import BusinessFactory, CategoryFactory, ProductFactory


@pytest.mark.django_db
class TestCreateProduct:

    def test_create_product(self):
        from apps.products.services import create_product
        biz = BusinessFactory()
        cat = CategoryFactory(business=biz)
        product = create_product(
            biz,
            name="Velvet Rose Perfume",
            selling_price=Decimal("3500"),
            category=cat,
            status="active",
        )
        assert product.id is not None
        assert product.name == "Velvet Rose Perfume"
        assert product.slug == "velvet-rose-perfume"
        assert product.category == cat

    def test_create_product_increments_business_counter(self):
        from apps.products.services import create_product
        biz = BusinessFactory()
        initial_count = biz.total_products
        create_product(biz, name="Test Product", selling_price=Decimal("1000"), status="active")
        biz.refresh_from_db()
        assert biz.total_products == initial_count + 1

    def test_create_product_increments_category_counter(self):
        from apps.products.services import create_product
        biz = BusinessFactory()
        cat = CategoryFactory(business=biz)
        create_product(biz, name="Test", selling_price=Decimal("500"), category=cat, status="active")
        cat.refresh_from_db()
        assert cat.product_count == 1


@pytest.mark.django_db
class TestAdjustStock:

    def test_add_stock(self):
        from apps.products.services import adjust_stock
        product = ProductFactory(stock_quantity=10)
        product = adjust_stock(product, quantity_delta=20, reason="Restocked")
        assert product.stock_quantity == 30

    def test_remove_stock(self):
        from apps.products.services import adjust_stock
        product = ProductFactory(stock_quantity=50)
        product = adjust_stock(product, quantity_delta=-10, reason="Damaged goods")
        assert product.stock_quantity == 40

    def test_negative_stock_raises_error(self):
        from apps.products.services import adjust_stock
        product = ProductFactory(stock_quantity=5)
        with pytest.raises(ValueError, match="negative stock"):
            adjust_stock(product, quantity_delta=-10)

    def test_creates_audit_record(self):
        from apps.products.services import adjust_stock
        from apps.inventory.models import StockAdjustment
        product = ProductFactory(stock_quantity=20)
        adjust_stock(product, quantity_delta=5, reason="Test adjustment")
        adj = StockAdjustment.objects.filter(product=product).first()
        assert adj is not None
        assert adj.quantity_delta == 5
        assert adj.previous_stock == 20
        assert adj.new_stock == 25


@pytest.mark.django_db
class TestProductStockStatus:

    def test_in_stock(self):
        product = ProductFactory(stock_quantity=50, low_stock_threshold=5)
        assert product.stock_status == "in-stock"

    def test_low_stock(self):
        product = ProductFactory(stock_quantity=3, low_stock_threshold=5)
        assert product.stock_status == "low-stock"

    def test_out_of_stock(self):
        product = ProductFactory(stock_quantity=0)
        assert product.stock_status == "out-of-stock"
