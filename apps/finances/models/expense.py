"""
Expense model — manual cost entries for the business.

Revenue comes from completed orders (read from orders table).
Expenses are manually entered by the business owner.
Together they produce the FinanceSummary.
"""
from django.db import models
from apps.core.models import BaseModel

EXPENSE_CATEGORY_CHOICES = [
    ("stock_purchases", "Stock Purchases"),
    ("staff_salaries", "Staff Salaries"),
    ("rent_utilities", "Rent & Utilities"),
    ("marketing", "Marketing"),
    ("delivery_costs", "Delivery Costs"),
    ("equipment", "Equipment"),
    ("other", "Other"),
]


class Expense(BaseModel):

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="expenses",
        db_index=True,
    )

    category = models.CharField(
        max_length=50,
        choices=EXPENSE_CATEGORY_CHOICES,
        default="other",
        db_index=True,
    )
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(db_index=True)

    class Meta:
        db_table = "finances_expense"
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.description} — KSh {self.amount} ({self.date})"
