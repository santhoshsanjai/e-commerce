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

To fill the shop with 50 sample products (5 categories, each product with a picture), run this
while the stack is up. Running it again adds nothing new, and it refuses to run in production:

```bash
docker compose run --rm --build api python -m app.cli seed-sample-products
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
| `MFA_ENCRYPTION_KEY` | Required outside local/test. Fernet key that encrypts staff authenticator secrets (see below) |
| `STAFF_MFA_REQUIRED` | Two-step sign-in for staff; `true` by default and required in production |
| `EMAIL_BACKEND` | `smtp` (Mailpit locally) or `ses` when deployed; see `backend/.env.example` |
| `FORWARDED_ALLOW_IPS` | Proxies whose `X-Forwarded-For` is trusted (load balancer and web subnets, e.g. the VPC CIDR). Never `*` when deployed |

The web containers (`frontend/nginx.conf`) take `API_UPSTREAM` (where `/api` goes) and
`MEDIA_ORIGIN` (the CDN origin for product images, allowed by the Content Security Policy).

## Staff two-step sign-in

Staff sign in with their password and a 6-digit code from an authenticator app (Google
Authenticator, Microsoft Authenticator, 1Password and similar). At their first sign-in they scan a
QR code and are shown ten one-time recovery codes for a lost phone.

- A Super Admin can reset a staff member's two-step sign-in on their staff page (lost or new phone).
- If the only Super Admin loses their phone and their recovery codes, run this where the API runs:
  `python -m app.cli reset-mfa --email them@example.com`.
- Make the encryption key once per environment and keep it in the secrets store. Losing it means
  every staff member sets up their app again:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Look and feel: colours, name and announcement

Every colour in both apps is a design token (`--color-*`) defined once in
`frontend/projects/shared/styles/_tokens.scss`; components never hard-code colours, and hover shades and
tints are derived with `color-mix()`. Staff with the **settings.manage** permission (Super Admin and
Admin by default) can change the shop's name, the trust bar message under the header and any of these colours in
**Admin → Storefront**, starting from a ready-made palette if they like. Changes preview live in the
admin portal and are saved by the API (`/api/v1/admin/storefront`); both apps read them at start-up
from the public `/api/v1/storefront`.

To make another colour editable, add the variable to `_tokens.scss` and an entry to
`THEME_COLOR_GROUPS` in `frontend/projects/shared/src/lib/storefront/theme-colors.ts`.

Type is self-hosted (Inter for everything, with the system UI font as fallback) so the Content Security Policy
stays `font-src 'self'`. Animations (page transitions, scroll reveals, hover effects, loading
skeletons) all switch off for visitors who ask their device for reduced motion.

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

CI (`.github/workflows/ci.yml`) runs all of these on every pull request, plus Docker image builds, a
dependency audit and the end-to-end tests against the full Docker stack.

## End-to-end tests

Playwright tests in `e2e/` drive both apps in a real browser through the full journey: staff add a
product, a buyer orders it, staff dispatch it, import the courier file, and check the reports and audit
log. They also cover staff access by role, the buyer account page and phone layouts.

```bash
# 1. Start the stack (or run the dev servers on ports 4200, 4300 and 8000)
docker compose up --build -d
docker compose run --rm api python -m app.cli create-superadmin

# 2. Run the tests (they create their own data with unique names, so they can run repeatedly).
#    The password reset test reads email from Mailpit (http://localhost:8025, in docker-compose).
cd e2e
npm ci
npx playwright install chromium
E2E_ADMIN_EMAIL=you@example.com E2E_ADMIN_PASSWORD=... npx playwright test
npx playwright show-report   # after a failure
```

Never point these tests at production: they create real orders and staff accounts.

## Database migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"   # review the generated file
uv run alembic upgrade head
uv run alembic downgrade -1
```

Migrations are a controlled release step; the API never creates tables on start-up. Keep each one
backwards compatible for one release (add columns and tables; drop or rename them in a later
release), so a deploy can be rolled back to the previous image.

## Deployment

AWS infrastructure (Terraform) and the staging deploy pipeline are described in
[infra/README.md](infra/README.md).

## Operations

Health checks, logs, alerts, backups, restoring and secret rotation are in
[docs/operations.md](docs/operations.md). `ops/` has the backup, restore and restore-drill scripts.

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
  - Phase 2 complete.
- **Phase 3 (hardening and operations), complete:** end-to-end tests, security headers and rate
  limits, password reset, two-step sign-in for staff, health checks, logs, backups and the AWS
  staging setup ([infra/README.md](infra/README.md)).
- **Phase 4 (payments, email, tax), in progress:**
  - Order emails to buyers: confirmed, shipped, out for delivery, delivered, delivery failed,
    cancelled and returned. Sent through an outbox so none is lost if email is briefly down
    ([docs/operations.md](docs/operations.md#emails-to-buyers)). Locally they arrive in Mailpit
    (http://localhost:8025) when the API runs with `EMAIL_BACKEND=smtp`.
