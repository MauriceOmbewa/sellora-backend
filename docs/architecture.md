# Sellora Backend — Architecture Notes

## Stack
- Python 3.12 / Django 5.1 / Django REST Framework 3.15
- PostgreSQL 16
- Redis 7 (cache + Celery broker)
- Celery 5.4 (background tasks)

## Request Flow

```
Request
  └── TenantMiddleware       (attaches business to request from URL)
  └── AuthenticationMiddleware (JWT validation)
  └── LoggingMiddleware
        └── View             (thin — validates input, calls service)
              └── Service    (business logic)
                    └── Selector / ORM  (data access)
```

## App Domains

| App | Responsibility |
|-----|---------------|
| accounts | User model, Google OAuth, JWT |
| businesses | Business, BusinessSettings, StorefrontSettings |
| products | Product, ProductImage |
| categories | Category |
| inventory | InventoryView (computed), StockAdjustment |
| customers | Customer |
| orders | Order, OrderItem, OrderTimeline |
| payments | Payment stubs (future Stripe / M-PESA) |
| finances | Expense, FinanceSummary (computed) |
| analytics | AnalyticsSummary (computed) |
| notifications | Notification preferences + Celery tasks |
| messages | Customer inquiries (contact form) |
| core | Shared abstract models |

## Multi-Tenancy

Every entity is scoped to a `Business`. The URL structure enforces this:
`/api/v1/businesses/{business_id}/products/`

`TenantMiddleware` resolves the `business_id` from the URL and attaches the
`Business` instance to `request.business`. Permission classes verify the
authenticated user owns that business.

## Public Storefront API

Routes under `/api/v1/store/{slug}/` are unauthenticated. The slug is resolved
to a Business in `TenantMiddleware`. `costPrice` is never serialized on these routes.
