"""
Pricing plan definitions for Sellora SaaS.

These are the plans visible on the marketing/landing page and in the
Settings → Billing tab. Plan assignment lives on Business.plan field.

Prices are in KES (Kenyan Shillings).
"""

PRICING_PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "monthly_price": 0,
        "annual_price": 0,
        "description": "Perfect for new businesses getting started online.",
        "features": [
            "1 storefront",
            "Up to 50 products",
            "Order management",
            "Basic analytics",
            "Email support",
        ],
        "highlighted": False,
        "cta_text": "Get started free",
    },
    {
        "id": "business",
        "name": "Business",
        "monthly_price": 3499,
        "annual_price": 34990,
        "description": "For growing businesses that need more power and visibility.",
        "features": [
            "1 storefront",
            "Unlimited products",
            "Advanced analytics",
            "Custom domain",
            "Email + SMS notifications",
            "Priority support",
            "Inventory management",
            "Financial reports",
        ],
        "highlighted": True,
        "cta_text": "Start Business plan",
    },
    {
        "id": "growth",
        "name": "Growth",
        "monthly_price": 7999,
        "annual_price": 79990,
        "description": "For established businesses scaling fast.",
        "features": [
            "Multiple storefronts",
            "Unlimited products",
            "Advanced analytics + exports",
            "Custom domain",
            "Email + SMS + WhatsApp notifications",
            "Dedicated support",
            "Inventory management",
            "Financial reports + exports",
            "API access",
            "Team accounts (coming soon)",
        ],
        "highlighted": False,
        "cta_text": "Start Growth plan",
    },
]

PLAN_IDS = [p["id"] for p in PRICING_PLANS]
