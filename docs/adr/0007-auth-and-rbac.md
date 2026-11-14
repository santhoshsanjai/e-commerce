# ADR 0007: Authentication and role-based access

**Status:** Accepted · 2026-11-14

## Decision
- **One `users` table** with `user_type` BUYER or STAFF. Buyers log in at `/api/v1/auth/login`, staff at
  `/api/v1/auth/staff/login`; each route refuses the other type. Staff accounts are created only by staff
  holding `users.manage`; only a Super Admin can grant the Super Admin role.
- **Passwords** hashed with Argon2id. Login responses do not reveal whether an email exists. Login is
  rate-limited per IP and email (in-process for now; moves to a shared store before running multiple
  API instances).
- **Tokens:** a 15-minute JWT access token (audience `buyer` or `staff`) held in memory by the Angular app,
  and an opaque refresh token in an `httpOnly`, `SameSite=Strict` cookie scoped to `/api/v1/auth`. Refresh
  tokens rotate on every use; replaying a rotated token revokes the whole session family.
- **RBAC:** roles hold permissions; a user's permissions are the union over their roles (handoff question
  10 default: multiple roles allowed, no regional scoping). Every admin endpoint declares
  `require_permission("…")`; a test fails if an admin route is missing from the permission matrix.
  The admin UI hides menus by permission for convenience only.
- **Seeded roles:** Super Admin (all permissions), Admin and Manager, with defaults in
  `app/modules/access_control/permissions.py`, editable later by a Super Admin.
- **Audit:** staff logins and staff creation are written to `audit_logs`; later modules add product
  publication, exports, imports and status overrides.

## Deferred
TOTP MFA for Super Admin and Admin (Phase 2), password reset by email (Phase 3).
