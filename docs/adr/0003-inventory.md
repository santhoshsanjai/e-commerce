# ADR 0003: Exact stock quantity per SKU

**Status:** Provisional · 2026-11-14 · answers handoff question 2

## Decision
Store an integer `stock_qty` (never negative, enforced by a check constraint) on each SKU. Stock is
decremented inside the order-creation transaction with a row lock (`SELECT ... FOR UPDATE`) and restored
on cancellation. Buyers see "In stock", "Low stock" or "Out of stock" rather than exact counts.
Low-stock alerts to staff are deferred.

## What changes if revisited
If only in/out-of-stock is wanted, staff can enter a large quantity or we add an "untracked" flag; the
checkout logic stays the same.
