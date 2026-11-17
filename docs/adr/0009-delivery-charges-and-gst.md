# ADR 0009: Delivery charges and GST set in the admin portal

**Status:** Provisional · 2026-11-17 · answers handoff question 8 with configurable defaults

## Context
The handoff leaves shipping charges, tax/GST and invoices open (question 8). Hard-coding any rule
would mean a code change each time the business decides.

## Decision
- A **Delivery and GST** page in the admin portal (permission `settings.manage`) holds the rules:
  a flat delivery charge per order, an optional "free delivery from ₹X" subtotal, whether product
  prices **include** GST (the default, as Indian MRPs do) or GST is **added** at checkout, and a
  default GST rate.
- Each product can have its own GST rate (0 to 40%; the usual slabs are 0, 5, 18 and 40%). Blank
  means the shop default, 18% until changed.
- GST is worked out per order line and rounded to the paisa, half up. The cart, checkout, order
  pages and emails all use the same calculation (`app/modules/pricing/service.py`).
- Every order stores its GST rate and amount per line, the total GST, and whether prices
  included it. Later rule changes never alter placed orders.

## Consequences
- With "prices include GST" the totals buyers pay are unchanged. Pages show "Includes GST of ₹X".
- CGST/SGST versus IGST split, the seller's GSTIN, HSN codes and tax invoices are not built yet.
  They need the business's GST registration details, and the stored per-line rate and amount are
  what an invoice will use.

## What changes if revisited
Delivery charges by region or weight would replace the flat fee in `pricing.quote`. Discounts
and coupons would fill the existing `discount_minor` columns.
