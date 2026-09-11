# Sellora Backend

Django + PostgreSQL backend for the Sellora SaaS platform — a multi-tenant e-commerce solution that lets businesses create and manage their own online storefronts.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5.1 + Django REST Framework 3.15 |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Background Tasks | Celery 5.4 |
| Auth | Google OAuth 2.0 + JWT (SimpleJWT) |
| API Docs | drf-spectacular (Swagger + ReDoc) |
| Storage | Local (dev) / AWS S3 (production) |

---

## Project Structure

```
sellora-backend/
│
├── manage.py
│
├── config/                     # Django project configuration
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── development.py      # Local dev overrides
│   │   ├── testing.py          # Test runner settings
│   │   └── production.py       # Production settings
│   ├── urls.py                 # Root URL configuration
│   ├── celery.py               # Celery app
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                       # Business domain apps
│   ├── accounts/               # Users, Google OAuth, JWT
│   ├── businesses/             # Business profiles, settings, storefront config
│   ├── products/               # Product catalogue
│   ├── categories/             # Product categories
│   ├── inventory/              # Stock management
│   ├── customers/              # Customer records
│   ├── orders/                 # Order processing
│   ├── payments/               # Payment stubs (Stripe / M-PESA)
│   ├── finances/               # Expenses, financial reports
│   ├── analytics/              # Dashboard analytics
│   ├── notifications/          # Email / SMS alerts
│   ├── messages/               # Customer inquiries (contact form)
│   └── core/                   # Shared abstract models
│
├── api/
│   └── v1/
│       └── urls.py             # Versioned API URL dispatcher
│
├── middleware/
│   ├── tenant.py               # Business/tenant resolution from URL
│   ├── logging.py              # Request logging
│   └── authentication.py      # Auth middleware stub
│
├── common/
│   ├── exceptions/             # Custom exceptions + global handler
│   ├── pagination/             # Standard paginator
│   ├── responses/              # Success/error response helpers
│   ├── permissions/            # Shared permission classes
│   ├── validators/             # Shared validators
│   ├── decorators/             # Utility decorators
│   └── utilities/              # Misc helpers
│
├── tests/                      # Top-level test structure (mirrors apps/)
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   ├── testing.txt
│   └── production.txt
├── scripts/                    # Management scripts
├── docs/                       # Architecture notes
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

Each app follows the same internal structure:

```
apps/<domain>/
├── models/         # Database models
├── views/          # API endpoint handlers (thin)
├── serializers/    # Request/response serialization
├── services/       # Business logic
├── selectors/      # Read/query logic
├── migrations/
├── tests/
├── admin.py
├── urls.py
├── permissions.py
├── signals.py
├── tasks.py        # Celery tasks
└── constants.py
```

---

## API Overview

### Authentication
All dashboard endpoints require a `Bearer` JWT token in the `Authorization` header.

```
POST   /api/v1/auth/google        Exchange Google ID token → JWT
GET    /api/v1/auth/me            Current user info
POST   /api/v1/auth/signout       Invalidate token
```

### Dashboard API (authenticated)
All business-scoped endpoints follow this pattern:

```
/api/v1/businesses/{business_id}/<resource>/
```

| Resource | Endpoints |
|---|---|
| Businesses | CRUD, settings |
| Products | CRUD, status, availability |
| Categories | CRUD |
| Inventory | List, stock adjustment |
| Orders | CRUD, status transitions |
| Customers | List, detail + order history |
| Finances | Expenses CRUD, summary report |
| Analytics | Summary, time-series (7d/30d/90d) |
| Messages | List, mark read/replied |

### Public Storefront API (no auth)
Keyed by business slug:

```
/api/v1/store/{slug}/products/
/api/v1/store/{slug}/products/{product_slug}/
/api/v1/store/{slug}/categories/
/api/v1/store/{slug}/orders/         POST — place order
/api/v1/store/{slug}/messages/       POST — contact form
```

### API Documentation
Available at `/api/docs/` (Swagger UI) and `/api/redoc/` when the server is running.

---

## Local Development Setup

### Prerequisites
- Python 3.12
- PostgreSQL 16
- Redis 7 (for Celery — optional in early development)

### 1. Clone and create virtualenv

```bash
git clone <repo-url>
cd sellora-backend

python3.12 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements/development.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `DJANGO_SECRET_KEY` — any long random string
- `DATABASE_URL` — your local Postgres connection string
- `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` — from Google Cloud Console

### 4. Create the database

```bash
# Start PostgreSQL if not running
brew services start postgresql@16

# Create DB and user
/usr/local/opt/postgresql@16/bin/psql -U <your-mac-user> -d postgres -c "CREATE USER sellora WITH PASSWORD 'sellora_dev_pass' CREATEDB;"
/usr/local/opt/postgresql@16/bin/createdb -U <your-mac-user> sellora_dev
/usr/local/opt/postgresql@16/bin/psql -U <your-mac-user> -d postgres -c "GRANT ALL ON SCHEMA public TO sellora; ALTER DATABASE sellora_dev OWNER TO sellora;"
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

API available at `http://localhost:8000/api/v1/`
Swagger docs at `http://localhost:8000/api/docs/`

---

## Running with Docker

```bash
docker-compose up --build
```

This starts PostgreSQL, Redis, the Django backend, and a Celery worker together.

---

## Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=apps --cov-report=html

# Single app
pytest tests/accounts/
```

---

## Multi-Tenancy

Every business is an isolated tenant. The URL structure enforces this:

```
/api/v1/businesses/{business_id}/products/
```

`TenantMiddleware` extracts the `business_id` from the URL on every request. Permission classes then verify the authenticated user owns that business before any data is touched.

The public storefront uses a slug instead of an ID:

```
/api/v1/store/{slug}/...
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `REDIS_URL` | Redis connection string |
| `CELERY_BROKER_URL` | Celery broker (Redis) |
| `FRONTEND_URL` | Frontend origin for CORS |
| `USE_S3` | `True` to use S3 for file storage |

---

## Build Phases

| Phase | Steps | Status |
|---|---|---|
| 1 — Foundation | Environment, scaffold, base config | ✅ Done |
| 2 — Core infrastructure | Common layer, middleware, accounts + Google OAuth | 🔄 Next |
| 3 — Business domain | Businesses, categories, products | Pending |
| 4 — Commerce | Customers, orders, inventory | Pending |
| 5 — Financial & reporting | Finances, analytics | Pending |
| 6 — Notifications & messaging | Celery tasks, messages | Pending |
| 7 — Public storefront API | All /store/:slug/ endpoints | Pending |
| 8 — Admin, uploads, billing | Django admin, S3, plans | Pending |
| 9 — Quality & deployment | Tests, docs, production config | Pending |
