"""
Inventory URL patterns.
Mounted at /api/v1/businesses/{business_id}/inventory/

GET    /           Inventory list (all products with stock info)
POST   /adjust/    Adjust stock for a product
GET    /history/   Stock adjustment audit log
"""
from django.urls import path
from apps.inventory.views import (
    InventoryListView,
    StockAdjustmentHistoryView,
    StockAdjustView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("adjust/", StockAdjustView.as_view(), name="inventory-adjust"),
    path("history/", StockAdjustmentHistoryView.as_view(), name="inventory-history"),
]
