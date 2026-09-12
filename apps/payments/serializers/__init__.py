from rest_framework import serializers
from apps.payments.constants import PRICING_PLANS


class PricingPlanSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    monthly_price = serializers.IntegerField()
    annual_price = serializers.IntegerField()
    description = serializers.CharField()
    features = serializers.ListField(child=serializers.CharField())
    highlighted = serializers.BooleanField()
    cta_text = serializers.CharField()


class BillingInfoSerializer(serializers.Serializer):
    """Current billing state for a business."""
    plan = serializers.CharField()
    plan_name = serializers.CharField()
    monthly_price = serializers.IntegerField()
    next_billing_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()


class PlanUpgradeSerializer(serializers.Serializer):
    """Validates POST /businesses/{id}/billing/upgrade/"""
    plan = serializers.ChoiceField(choices=["starter", "business", "growth"])


class PlanCancelSerializer(serializers.Serializer):
    """Validates POST /businesses/{id}/billing/cancel/"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")
