# ADR 0004: Login required to check out

**Status:** Provisional · 2026-11-14 · answers handoff question 3

## Decision
Browsing is public. Adding to cart and checkout require a buyer account, matching flow 5.1 in the handoff.
Orders always belong to a user, which simplifies order history, IDOR checks and courier contact details.

## What changes if revisited
Guest checkout would add a nullable `user_id` on orders, an email-based order lookup with a signed link,
and a cart stored by anonymous session. Medium effort; no change to existing orders.
