# ADR 0005: Cash on delivery first, behind a payment interface

**Status:** Provisional · 2026-11-14 · answers handoff question 4

## Decision
Checkout supports cash on delivery (COD) only in the first slice: a COD order is created as CONFIRMED with
payment status PENDING. Payment logic sits behind a `PaymentProvider` interface in
`app/infrastructure/payment_provider.py` (added with checkout). An online gateway is added in Phase 4 once
the provider is chosen, and its success is accepted only from a verified, signed webhook.

## What changes if revisited
Online payment adds a PENDING_PAYMENT order state, the provider adapter and webhook endpoint. COD can be
kept, limited by region or order value, or switched off by configuration.
