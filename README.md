# E-Commerce Platform

Buyer website and admin portal for a single-merchant e-commerce platform.

| Part | Stack | Path |
| --- | --- | --- |
| Buyer website | Angular 22 | `frontend/projects/buyer` |
| Admin portal | Angular 22 | `frontend/projects/admin` |
| Shared UI, auth, tokens | Angular library `@shop/shared` | `frontend/projects/shared` |
| API | FastAPI, SQLAlchemy 2, Alembic, Python 3.13 | `backend/` |
| Database | PostgreSQL 18 | via Docker |
| Decisions | ADRs | `docs/adr/` |

## Quick start (Docker)

Requires Docker Desktop (or Docker Engine with Compose v2).

```bash
docker compose up --build
# create the first Super Admin (password is prompted, never in shell history)
docker compose run --rm api python -m app.cli create-superadmin --email you@example.com --name "Your Name"
```

- Buyer site: http://localhost:4200
- Admin portal: http://localhost:4300
- API docs (OpenAPI): http://localhost:8000/docs
- Product media (local S3): http://localhost:8333/product-media

Migrations run in the one-off `migrate` service before the API starts.

## Local development without Docker for the apps

Prerequisites: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node.js 22.22+ and npm, a PostgreSQL 18
database and S3-compatible storage (`docker compose up -d db s3 s3-setup` starts both).

```bash
# Backend
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.cli create-superadmin --email you@example.com --name "Your Name"
uv run uvicorn app.main:app --reload            # http://localhost:8000

# Frontend (second terminal)
cd frontend
npm ci
npm run start:buyer                              # http://localhost:4200
npm run start:admin                              # http://localhost:4300
```

The Angular dev servers proxy `/api` to `localhost:8000` (`frontend/proxy.conf.json`), so the browser sees
one origin and the refresh cookie works without CORS.

## Environment variables (backend)

See `backend/.env.example`. The important ones:

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | `local`, `test`, `dev`, `staging` or `production` |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@host:5432/db` |
| `JWT_SECRET` | Required outside local/test; at least 32 random characters |
| `COOKIE_SECURE` | `true` wherever the site is served over HTTPS (required in production) |
| `CORS_ORIGINS` | JSON list of allowed browser origins |

## Checks

```bash
# Backend (needs PostgreSQL on localhost:5432; tests create and drop `ecommerce_test`)
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest

# Frontend
cd frontend
npm run format:check && npm run lint && npm test && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of these on every pull request, plus Docker image builds and a
dependency audit.

## Database migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"   # review the generated file
uv run alembic upgrade head
uv run alembic downgrade -1
```

Migrations are a controlled release step; the API never creates tables on start-up.

## Project status

- **Phase 0 (foundations):** auth for buyers and staff, RBAC with seeded Super Admin, Admin and Manager
  roles, audit log, both app shells, Docker, CI.
- **Phase 1 (vertical slice), complete:**
  - Catalogue: categories, products with SKUs, images, publish rules, buyer listing and product page.
  - Cart and checkout: saved addresses (Indian PIN codes), server-side cart, cash-on-delivery checkout
    that locks stock and is safe to retry (`Idempotency-Key` header), order confirmation, My orders,
    admin order list (search, status and date filters) and order detail with status history.
  - Dispatch: staff pick confirmed orders into a batch; the orders move to "Handed to courier" and a
    courier Excel file is generated, kept in the private bucket and downloadable again later. Every
    batch and download is audited. Format: [docs/courier-file-format.md](docs/courier-file-format.md).
  - Courier import: staff upload the courier's status file, see a row-by-row preview (what changes,
    what's unchanged, what's wrong), then apply it once. Re-uploading the same file changes
    nothing. The courier fills AWB No, Courier Status and Status Date on our own export and sends it
    back (ADR 0008).
  - Manual status updates on the order page, following the lifecycle map; stepping outside it needs
    `orders.status.override` and a reason. Cancelling before handover restocks; cash on delivery is
    marked paid when delivered; delivered orders are completed by hand.
- **Phase 2 (admin operations), in progress:**
  - Dashboard: today's orders and sales, sales for the last 7 days (Indian calendar days), cash on
    delivery still with the courier, open orders by status, and a "needs attention" list (orders
    waiting for dispatch, failed deliveries, unapplied courier files, low stock).
  - Audit log viewer: search by person or record, filter by action and date, see before/after values.
  - Staff and roles: add staff, edit their details and roles, reset a password, deactivate or
    reactivate (deactivating signs them out everywhere at once). Create custom roles and edit which
    permissions each role has. Safeguards, enforced by the API: only a Super Admin can grant the
    Super Admin role or change a Super Admin's account; nobody can change their own roles or
    deactivate themselves; there is always at least one active Super Admin; the Super Admin role
    always keeps every permission; built-in roles can't be renamed or deleted; and nobody can grant
    a permission they don't hold. Every change is in the audit log.
  - Sales report: pick a date range (or a quick range such as last month) and show by day, week or
    month. Shows sales, orders, average order, items sold, delivered value, cash on delivery
    collected, cancellations and returns, sales by state and top products. "Download Excel" gives
    the same figures plus every product and every order in the range; each download is audited.
  - Buyer account page: change name and mobile number, manage saved delivery addresses (add, edit,
    make default, remove), and change password. Changing the password signs out every other device
    and keeps this one signed in; wrong-password attempts share the login rate limit.
  - Phase 2 complete. Next: Phase 3 (security review, backups, monitoring, staging, then
    production).
