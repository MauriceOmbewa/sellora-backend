from rest_framework import serializers
from apps.finances.models import Expense, EXPENSE_CATEGORY_CHOICES


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "category", "description", "amount", "date",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExpenseCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=EXPENSE_CATEGORY_CHOICES)
    description = serializers.CharField(max_length=500)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    date = serializers.DateField()


class ExpenseUpdateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=EXPENSE_CATEGORY_CHOICES, required=False)
    description = serializers.CharField(max_length=500, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2,
                                      min_value=0, required=False)
    date = serializers.DateField(required=False)


class FinanceSummarySerializer(serializers.Serializer):
    """Read-only computed financial summary."""
    period = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    cost_of_goods = serializers.DecimalField(max_digits=12, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    gross_margin = serializers.FloatField()
    net_margin = serializers.FloatField()
