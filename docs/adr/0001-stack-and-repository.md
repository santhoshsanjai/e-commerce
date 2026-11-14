# ADR 0001: Stack and repository layout

**Status:** Accepted · 2026-11-14

## Context
The handoff fixes the stack: Angular 22, FastAPI, PostgreSQL 18, SQLAlchemy 2 with Alembic, S3-compatible
media and Docker. It suggests an Nx or Angular workspace with two apps and shared libraries.

## Decision
- One monorepo: `backend/` (FastAPI modular monolith), `frontend/` (Angular CLI workspace), `docs/`,
  `.github/workflows/`, `docker-compose.yml`.
- Frontend uses the **Angular CLI multi-project workspace** (`projects/buyer`, `projects/admin`,
  `projects/shared`) rather than Nx. It meets the "two apps plus shared libraries" requirement with fewer
  moving parts and no dependency on Nx's Angular 22 support cadence. We can migrate to Nx if build times
  or library count make it worthwhile.
- Backend uses synchronous SQLAlchemy sessions with sync route handlers. FastAPI runs them in a thread
  pool, which keeps transactions and row locks simple. Async is used only where the whole I/O path is async.
- Python dependencies are managed with uv (`uv.lock`), Node with npm (`package-lock.json`); exact versions
  are locked.
- Tests run against real PostgreSQL 18, never SQLite.

## Consequences
Both apps build and deploy independently from one repository. Shared code lives in `@shop/shared`.
