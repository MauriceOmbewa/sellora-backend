# Sellora Backend

Django + PostgreSQL backend for the Sellora SaaS platform — a multi-tenant e-commerce solution that lets businesses create and manage their own online storefronts.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [How This Differs From a Default Django Project](#how-this-differs-from-a-default-django-project)
- [Project Structure](#project-structure)
- [Inside Each App](#inside-each-app)
  - [The Service-Selector Pattern](#the-service-selector-pattern)
- [Where to Make Changes](#where-to-make-changes)
- [Shared Utilities in common/](#shared-utilities-in-common)
- [Base Models](#base-models-appcore)
- [Settings — How the Split Works](#settings--how-the-split-works)
- [Multi-Tenancy](#multi-tenancy)
- [Authentication](#authentication)
- [API Overview](#api-overview)
- [Local Development Setup](#local-development-setup)
- [Running with Docker](#running-with-docker)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [Build Phases](#build-phases)

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

## How This Differs From a Default Django Project

When you run `django-admin startproject myproject`, Django creates this:

```
myproject/
├── manage.py
└── myproject/
    ├── __init__.py
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
```

Then you add apps with `python manage.py startapp myapp`, which gives each one flat files — `models.py`, `views.py`, `urls.py`, etc. — all in a single directory.

This project keeps all the same Django concepts but reorganizes them for a production, multi-app codebase. Nothing is missing — it's all just in better places. Here is the direct mapping:

| Default Django | This Project | Why |
|---|---|---|
| `myproject/settings.py` | `config/settings/base.py` + `development.py` / `production.py` | Split by environment so secrets and debug flags never mix |
| `myproject/urls.py` | `config/urls.py` | Same role, just moved into the `config/` package |
| `myproject/wsgi.py` | `config/wsgi.py` | Same |
| `myproject/asgi.py` | `config/asgi.py` | Same |
| `manage.py` | `manage.py` | Unchanged, same location |
| `myapp/models.py` | `apps/myapp/models/` | A folder instead of a file so large apps split models across files |
| `myapp/views.py` | `apps/myapp/views/` | Same — folder for better organization |
| `myapp/serializers.py` | `apps/myapp/serializers/` | Same pattern |
| — | `apps/myapp/services/` | Business logic layer (write operations) |
| — | `apps/myapp/selectors/` | Query layer (read operations) |

The core rule: **the `config/` folder is where `myproject/` would normally be**, and **every Django app lives inside `apps/`** instead of at the root level.

---

## Project Structure

```
sellora-backend/
│
├── manage.py                       # Same as always — entry point for all Django commands
│
├── config/                         # ← This is your "myproject/" folder renamed
│   ├── settings/
│   │   ├── base.py                 # All shared settings (replaces settings.py)
│   │   ├── development.py          # Extends base — DEBUG on, permissive CORS, console email
│   │   ├── testing.py              # Extends base — used by pytest
│   │   └── production.py          # Extends base — HTTPS, Sentry, strict security headers
│   ├── urls.py                     # Root URL conf (replaces myproject/urls.py)
│   ├── celery.py                   # Celery app instance
│   ├── wsgi.py                     # WSGI entry point
│   └── asgi.py                     # ASGI entry point
│
├── apps/                           # ← All your Django apps go here, not at the root
│   ├── core/                       # Abstract base models — no endpoints, no views
│   ├── accounts/                   # Users, Google OAuth, JWT tokens
│   ├── businesses/                 # Business profiles + public storefront config
│   ├── products/                   # Product catalogue
│   ├── categories/                 # Product categories
│   ├── inventory/                  # Stock management
│   ├── customers/                  # Customer records
│   ├── orders/                     # Order processing
│   ├── payments/                   # Payment stubs (Stripe / M-PESA)
│   ├── finances/                   # Expenses and financial reports
│   ├── analytics/                  # Dashboard analytics
│   ├── notifications/              # Email / SMS alerts
│   └── messages/                   # Customer inquiries
│
├── api/                            # URL routing layer only — no logic lives here
│   ├── urls.py                     # Routes /api/ → /api/v1/
│   └── v1/
│       └── urls.py                 # Registers every app's urls.py under /api/v1/
│
├── middleware/                     # Custom Django middleware (plain Python, not a Django app)
│   ├── tenant.py                   # Extracts business_id / slug from URL, sets request.business
│   ├── logging.py                  # Logs METHOD PATH → STATUS (Xms) per request
│   └── authentication.py          # Pass-through stub (JWT auth handled by DRF per view)
│
├── common/                         # Shared DRF utilities — no models, no migrations
│   ├── exceptions/handler.py       # Normalizes all errors to {"success": false, "error": {...}}
│   ├── pagination/                 # StandardResultsPagination with success envelope
│   ├── responses/                  # success_response(), created_response(), no_content_response()
│   ├── permissions/                # Shared DRF permission classes
│   ├── validators/                 # Shared validators
│   ├── decorators/                 # Utility decorators
│   └── utilities/                  # Misc helpers
│
├── tests/                          # Top-level test suite (mirrors apps/ structure)
├── requirements/
│   ├── base.txt                    # Core deps — Django, DRF, JWT, Celery, Redis, etc.
│   ├── development.txt             # + pytest, black, flake8, debug toolbar, factory-boy
│   ├── testing.txt                 # base + pytest/factory-boy only
│   └── production.txt             # Production extras
├── scripts/                        # Management and utility scripts
├── docs/                           # Architecture notes
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Inside Each App

Every app under `apps/` follows the same internal structure. This is the biggest difference from default Django — instead of flat `models.py` and `views.py` files, each app has dedicated folders and layers.

```
apps/<domain>/
├── models/             # Data schema only. No logic.
│   └── __init__.py     # Re-exports all models from this folder
├── serializers/        # DRF serializers — input validation + output shaping
├── views/              # DRF views — thin HTTP layer, delegates all work
├── services/           # All write logic: create, update, delete, orchestration
├── selectors/          # All read/query logic: filtered querysets, aggregations
├── migrations/         # Django migrations — generated the same way as always
├── tests/
├── admin.py            # Django admin registration
├── apps.py             # AppConfig
├── constants.py        # App-specific enums and constants
├── permissions.py      # DRF permission classes specific to this app
├── signals.py          # Django signals
├── tasks.py            # Celery background tasks (auto-discovered)
├── urls.py             # URL patterns for this app
└── validators.py       # Custom validators
```

### The Service-Selector Pattern

The `services/` and `selectors/` folders are the main conceptual shift from default Django. The idea is to keep each layer doing exactly one job:

```
HTTP Request
     ↓
  View          → handles only HTTP: auth check, call the right service/selector, return response
     ↓
  Service       → handles all writes: create order, update stock, send notification
     ↓  (or)
  Selector      → handles all reads: get orders for business, filter products by category
     ↓
  Model         → defines the data shape, nothing else
```

In a default Django project you might write queryset logic directly in a view or a manager. Here:
- **If it's a read/query** → it goes in `selectors/`
- **If it's a write/mutation** → it goes in `services/`
- **Views never contain business logic** — they call a selector or service and return the result

This keeps everything testable and avoids views that grow to 200+ lines.

---

## Where to Make Changes

### Adding a model field
Edit the file in `apps/<your_app>/models/`. Then run:
```bash
python manage.py makemigrations
python manage.py migrate
```
Migrations work exactly the same as in a default Django project.

### Adding a new endpoint
1. Write the query in `apps/<app>/selectors/__init__.py`
2. Write any write logic in `apps/<app>/services/__init__.py`
3. Write the serializer in `apps/<app>/serializers/__init__.py`
4. Write the view in `apps/<app>/views/__init__.py`
5. Add the URL to `apps/<app>/urls.py`
6. If it's a new app, register it in `api/v1/urls.py` with one `path()` line

### Adding a setting
Edit `config/settings/base.py` for settings that apply everywhere, or the specific environment file (`development.py`, `production.py`) for environment-specific values.

### Adding a Celery task
Write it in `apps/<app>/tasks.py`. Celery auto-discovers all `tasks.py` files across installed apps — no registration needed.

### Registering a model in Django admin
Edit `apps/<app>/admin.py` — same as always.

### Running management commands
```bash
python manage.py <command>       # same as always
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser
python manage.py shell
```

### Adding a new app
```bash
# Create the app structure inside apps/
mkdir -p apps/newapp/{models,views,serializers,services,selectors,migrations,tests}
touch apps/newapp/{__init__,apps,admin,constants,permissions,signals,tasks,validators,urls}.py
touch apps/newapp/{models,views,serializers,services,selectors,migrations,tests}/__init__.py

# Register it in settings
# config/settings/base.py → LOCAL_APPS list → add "apps.newapp"

# Register its URLs
# api/v1/urls.py → add path("newapp/", include("apps.newapp.urls"))
```

---

## Shared Utilities in common/

`common/` is a plain Python package — no Django app, no migrations. It provides cross-cutting DRF concerns used by every app.

### Responses (`common/responses/`)
Use these helpers in every view instead of returning `Response()` directly:

```python
from common.responses import success_response, created_response, no_content_response

# Single object
return success_response(data=serializer.data)

# After creation
return created_response(data=serializer.data)

# After delete
return no_content_response()
```

All success responses share a consistent envelope:
```json
{ "success": true, "data": { ... } }
```

### Error handling (`common/exceptions/handler.py`)
You don't call this directly. Raise any standard DRF exception and it's automatically normalized:
```python
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied

raise NotFound("Product not found.")
```
Response:
```json
{ "success": false, "error": { "code": "not_found", "message": "Product not found." } }
```

### Pagination (`common/pagination/`)
Applied globally — any `list` view that returns a queryset is automatically paginated:
```json
{ "success": true, "count": 42, "next": "...", "previous": "...", "total_pages": 3, "results": [...] }
```
Default page size is 20. Client can pass `?page=2&page_size=50`.

---

## Base Models (`apps/core/`)

`apps/core` provides abstract base models that all domain models inherit from:

```python
from apps.core.models.base import BaseModel

class Product(BaseModel):
    name = models.CharField(max_length=255)
    # BaseModel already gives you: id (UUID), created_at, updated_at
```

- `BaseModel` — UUID primary key + `created_at` + `updated_at`
- `TimeStampedModel` — just `created_at` + `updated_at` (if you need timestamps without UUID PK)

UUID primary keys are used everywhere to prevent sequential ID enumeration and to support the multi-tenant architecture.

---

## Settings — How the Split Works

`manage.py` defaults to `config.settings.development`. You never have to think about this during local development.

```python
# config/settings/development.py
from .base import *          # pulls in everything from base.py

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True
# ... dev-only overrides
```

To use a different settings file:
```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py runserver
```

Or in `.env`:
```
DJANGO_SETTINGS_MODULE=config.settings.development
```

All secrets (`DATABASE_URL`, `DJANGO_SECRET_KEY`, etc.) are read from the `.env` file at the project root via `django-environ`. The settings files themselves never contain secrets.

---

## Multi-Tenancy

Every business is an isolated tenant. The URL structure enforces this:

```
/api/v1/businesses/{business_id}/products/
/api/v1/businesses/{business_id}/orders/
/api/v1/businesses/{business_id}/customers/
```

`TenantMiddleware` extracts the `business_id` UUID from the URL on every request and stores it on `request._tenant_business_id`. Permission classes then verify the authenticated user owns that business before any data is touched. This is lazy — no DB hit happens on requests that will 401 anyway.

The public storefront uses a business slug instead of an ID:

```
/api/v1/store/{slug}/products/
/api/v1/store/{slug}/orders/        ← POST to place an order (no auth)
```

---

## Authentication

Authentication is Google OAuth only — no username/password. The flow:

1. Frontend sends a Google ID token to `POST /api/v1/auth/google/`
2. Backend verifies the token with Google, creates or retrieves the user
3. Backend returns a JWT access token + refresh token
4. Frontend sends `Authorization: Bearer <access_token>` on all subsequent requests

JWT tokens are handled by SimpleJWT per-view via DRF's authentication classes. Token rotation is enabled — refreshing a token blacklists the old one.

---

## API Overview

### Authentication endpoints

```
POST   /api/v1/auth/google/        Exchange Google ID token → JWT pair
GET    /api/v1/auth/me/            Current user profile
POST   /api/v1/auth/token/refresh/ Refresh access token
POST   /api/v1/auth/signout/       Blacklist token (sign out)
```

### Dashboard API (JWT required)

All business-scoped endpoints follow this pattern:
```
/api/v1/businesses/{business_id}/<resource>/
```

| Resource | Base path |
|---|---|
| Businesses | `/api/v1/businesses/` |
| Products | `/api/v1/businesses/{id}/products/` |
| Categories | `/api/v1/businesses/{id}/categories/` |
| Inventory | `/api/v1/businesses/{id}/inventory/` |
| Orders | `/api/v1/businesses/{id}/orders/` |
| Customers | `/api/v1/businesses/{id}/customers/` |
| Finances | `/api/v1/businesses/{id}/finances/` |
| Analytics | `/api/v1/businesses/{id}/analytics/` |
| Messages | `/api/v1/businesses/{id}/messages/` |

### Public Storefront API (no auth)

```
GET    /api/v1/store/{slug}/
GET    /api/v1/store/{slug}/products/
GET    /api/v1/store/{slug}/products/{product_slug}/
GET    /api/v1/store/{slug}/categories/
POST   /api/v1/store/{slug}/orders/        Place an order
POST   /api/v1/store/{slug}/messages/      Contact form
```

### API Documentation

Available when the server is running:
- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- OpenAPI schema (JSON): `http://localhost:8000/api/schema/`

---

## Local Development Setup

### Prerequisites
- Python 3.12
- PostgreSQL 16
- Redis 7 (for Celery — optional in early development)

### 1. Clone and create a virtualenv

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

Edit `.env` and fill in at minimum:
- `DJANGO_SECRET_KEY` — any long random string
- `DATABASE_URL` — your local Postgres connection string (e.g. `postgres://sellora:password@localhost:5432/sellora_dev`)
- `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` — from Google Cloud Console

### 4. Create the database

```bash
# Create the DB user and database
psql -U postgres -c "CREATE USER sellora WITH PASSWORD 'sellora_dev_pass' CREATEDB;"
psql -U postgres -c "CREATE DATABASE sellora_dev OWNER sellora;"
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional, for Django admin)

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/docs/`
- Django admin: `http://localhost:8000/admin/`

---

## Running with Docker

```bash
docker-compose up --build
```

Starts PostgreSQL, Redis, the Django backend (gunicorn), a Celery worker, and Celery Beat together.

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

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `REDIS_URL` | Redis URL for cache |
| `CELERY_BROKER_URL` | Celery broker (Redis) |
| `CELERY_RESULT_BACKEND` | Celery result backend (Redis) |
| `FRONTEND_URL` | Frontend origin for CORS |
| `USE_S3` | `True` to use AWS S3 for file storage |
| `DEBUG` | `True` for development, `False` for production |

---

## Build Phases

| Phase | Steps | Status |
|---|---|---|
| 1 — Foundation | Environment, scaffold, base config | ✅ Done |
| 2 — Core infrastructure | Common layer, middleware, accounts + Google OAuth | 🔄 In progress |
| 3 — Business domain | Businesses, categories, products | Pending |
| 4 — Commerce | Customers, orders, inventory | Pending |
| 5 — Financial & reporting | Finances, analytics | Pending |
| 6 — Notifications & messaging | Celery tasks, messages | Pending |
| 7 — Public storefront API | All `/store/{slug}/` endpoints | Pending |
| 8 — Admin, uploads, billing | Django admin, S3, plans | Pending |
| 9 — Quality & deployment | Tests, docs, production config | Pending |
