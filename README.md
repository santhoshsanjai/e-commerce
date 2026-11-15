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
- **Phase 1 (vertical slice), in progress:** catalogue done (categories, products with SKUs, images,
  publish rules, buyer listing and product page). Next: cart and checkout, orders, courier export and
  import, completion.
