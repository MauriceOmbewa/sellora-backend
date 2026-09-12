"""Business domain constants — choice tuples used in models and serializers."""

BUSINESS_CATEGORY_CHOICES = [
    ("cosmetics", "Cosmetics"),
    ("perfumes", "Perfumes"),
    ("fashion", "Fashion"),
    ("accessories", "Accessories"),
    ("beauty", "Beauty"),
    ("gifts", "Gifts"),
    ("electronics", "Electronics"),
    ("food", "Food & Beverages"),
    ("other", "Other"),
]

BUSINESS_STATUS_CHOICES = [
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("suspended", "Suspended"),
]

BUSINESS_PLAN_CHOICES = [
    ("starter", "Starter"),
    ("business", "Business"),
    ("growth", "Growth"),
]

DEFAULT_THEME = {
    "primaryColor": "#7C3AED",
    "primaryHover": "#6D28D9",
    "accentColor": "#F59E0B",
    "backgroundColor": "#FFFFFF",
    "textColor": "#111827",
}

DEFAULT_CONTACT = {
    "phone": "",
    "whatsapp": "",
    "email": "",
    "address": "",
    "city": "",
    "country": "Kenya",
    "openingHours": "Mon–Fri: 8am – 6pm",
}

DEFAULT_SOCIAL_LINKS = {
    "instagram": "",
    "facebook": "",
    "tiktok": "",
    "twitter": "",
    "youtube": "",
}

DEFAULT_HERO = {
    "heading": "",
    "subheading": "",
    "ctaText": "Shop Now",
    "ctaSecondaryText": "Learn More",
    "imageUrl": "",
}
