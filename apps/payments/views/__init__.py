"""
Payments / Billing views.

These are stubs — the business logic for plan upgrades will hook into
Stripe or a local payment provider in a future sprint. The endpoints
are functional (they update the plan field) but do not yet process
real payments.
"""
import logging
from datetime import date, timedelta

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.payments.constants import PRICING_PLANS
from apps.payments.serializers import (
    BillingInfoSerializer,
    PlanCancelSerializer,
    PlanUpgradeSerializer,
    PricingPlanSerializer,
)
from common.responses import success_response

logger = logging.getLogger("apps")


class PricingPlansView(APIView):
    """
    GET /api/v1/plans/

    Returns all pricing plans. Public — used by the marketing/landing page
    and the Settings → Billing tab.
    No authentication required.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = PricingPlanSerializer(PRICING_PLANS, many=True)
        return success_response(data=serializer.data)


class BusinessBillingView(APIView):
    """
    GET /api/v1/businesses/{business_id}/billing/

    Returns the current billing state for a business:
    plan, monthly price, next billing date, status.

    STUB — next_billing_date is calculated as 30 days from today.
    In production this will come from the payment provider.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        business = request.business
        plan_data = next(
            (p for p in PRICING_PLANS if p["id"] == business.plan),
            PRICING_PLANS[0],
        )

        billing_info = {
            "plan": business.plan,
            "plan_name": plan_data["name"],
            "monthly_price": plan_data["monthly_price"],
            "next_billing_date": (
                date.today() + timedelta(days=30)
                if business.plan != "starter"
                else None
            ),
            "status": "active",
        }
        return success_response(
            data=BillingInfoSerializer(billing_info).data
        )


class BillingUpgradeView(APIView):
    """
    POST /api/v1/businesses/{business_id}/billing/upgrade/
    Body: { "plan": "business" | "growth" }

    STUB — updates plan field immediately without payment.
    In production: create a Stripe checkout session and redirect.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id):
        serializer = PlanUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_plan = serializer.validated_data["plan"]
        business = request.business

        if business.plan == new_plan:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Business is already on the {new_plan} plan.")

        business.plan = new_plan
        business.save(update_fields=["plan", "updated_at"])

        plan_data = next(p for p in PRICING_PLANS if p["id"] == new_plan)
        logger.info(
            "Business %s upgraded to plan: %s", business.id, new_plan
        )

        return success_response(
            data={"plan": new_plan, "plan_name": plan_data["name"]},
            message=f"Plan upgraded to {plan_data['name']}."
        )


class BillingCancelView(APIView):
    """
    POST /api/v1/businesses/{business_id}/billing/cancel/

    STUB — downgrades to starter plan.
    In production: cancel the Stripe subscription at period end.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id):
        serializer = PlanCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = request.business
        if business.plan == "starter":
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No active paid subscription to cancel.")

        previous_plan = business.plan
        business.plan = "starter"
        business.save(update_fields=["plan", "updated_at"])

        logger.info(
            "Business %s cancelled plan: %s → starter", business.id, previous_plan
        )

        return success_response(
            data={"plan": "starter"},
            message="Subscription cancelled. You've been moved to the Starter plan."
        )
