"""Finances services."""
import logging
from django.db import transaction
from apps.finances.models import Expense

logger = logging.getLogger("apps")


@transaction.atomic
def create_expense(business, *, category: str, description: str,
                   amount, date) -> Expense:
    expense = Expense.objects.create(
        business=business,
        category=category,
        description=description,
        amount=amount,
        date=date,
    )
    logger.info("Expense created: %s KSh %s for business %s",
                description, amount, business.id)
    return expense


@transaction.atomic
def update_expense(expense: Expense, **fields) -> Expense:
    allowed = {"category", "description", "amount", "date"}
    update_fields = []
    for field, value in fields.items():
        if field in allowed:
            setattr(expense, field, value)
            update_fields.append(field)
    update_fields.append("updated_at")
    expense.save(update_fields=update_fields)
    return expense


@transaction.atomic
def delete_expense(expense: Expense) -> None:
    expense.delete()
