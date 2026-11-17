# ADR 0010: Returns, refunds and buyer cancellation

**Status:** Provisional · 2026-11-17 · return window and refund method to confirm with the business

## Context
The plan lists returns and refunds for Phase 4. Payments are cash on delivery for now
([ADR 0005](0005-payments-cod-first.md)), so a refund is money sent back outside the app.

## Decision
- **Cancel before dispatch:** a buyer can cancel their own order while it is Confirmed or Packed.
  Stock goes back and the cancellation email is sent. After dispatch, a return is the way.
- **Return request:** within 7 days of delivery (`RETURN_WINDOW_DAYS`), a buyer picks the items,
  quantities and a reason. One open return per order; the buyer can withdraw it until it is
  approved.
- **Admin flow** (permission `returns.manage`; `returns.view` can read): Requested → Approved or
  Rejected (a note to the buyer is required) → Received (the returned quantities are restocked)
  → Refunded. Each step is audited and emails the buyer.
- **Refund:** recorded by the admin with the amount, method (UPI, bank transfer, cash or other)
  and reference. Only a paid order can be refunded, and never for more
  than its total. A full refund marks the order's payment as Refunded.

## Consequences
- The app records refunds; it does not move money. With an online payment provider, refunds to the
  card or wallet would call its API from `returns.service.refund`.
- Pickup scheduling with the courier is outside the app until the courier offers it.

## What changes if revisited
A different return window is a setting change. Partial restock (damaged items) would add a
"restock" flag per returned item.
