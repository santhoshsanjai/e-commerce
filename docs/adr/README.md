# Decision log

Each architecture or business decision is recorded as a short ADR. **Provisional** means we are
building to a recommended default while the business confirms; changing it later is expected and the
ADR says what that would cost.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-stack-and-repository.md) | Stack and repository layout | Accepted |
| [0002](0002-products-and-skus.md) | Every product has SKUs (variants-ready) | Provisional (handoff Q1) |
| [0003](0003-inventory.md) | Exact stock quantity per SKU | Provisional (handoff Q2) |
| [0004](0004-checkout-requires-login.md) | Login required to check out | Provisional (handoff Q3) |
| [0005](0005-payments-cod-first.md) | Cash on delivery first, behind a payment interface | Provisional (handoff Q4) |
| [0006](0006-country-and-currency.md) | One country and currency (India, INR) | Provisional (handoff Q9) |
| [0007](0007-auth-and-rbac.md) | Authentication and role-based access | Accepted |
| [0008](0008-courier-file-format.md) | Our own round-trip courier Excel format | Provisional (owner, 2026-11-14) |
| [0009](0009-delivery-charges-and-gst.md) | Delivery charges and GST set in the admin portal | Provisional (handoff Q8) |
| [0010](0010-returns-and-refunds.md) | Returns, refunds and buyer cancellation | Provisional |

Template: Context, Decision, Consequences, and (for provisional ADRs) What changes if revisited.
