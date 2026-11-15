# Courier file format

We use **one Excel sheet that goes out and comes back**:

1. Staff create a dispatch batch on the **Dispatch** page and download `DSP-YYYY-NNNNN.xlsx`.
2. The courier fills the three orange columns (**AWB No**, **Courier Status**, **Status Date**) and
   sends the same file back, as often as they like (for example, once a day).
3. Staff upload it on the **Courier import** page, check the preview and click **Apply**.

This is our own format ([ADR 0008](adr/0008-courier-file-format.md)). When we sign up with a
courier that has its own template, we change the two code tables listed at the end of this page.
No database change is needed.

## Sheet 1: Orders

One row per order, sorted by order date. Header row is frozen and filterable.

| Column | Filled by | Example | Notes |
| --- | --- | --- | --- |
| Order No | Us | ORD-2026-000123 | **Key used by the import. Don't change it.** |
| Order Date | Us | 14-11-2026 16:05 | Indian time (IST) |
| Consignee Name | Us | Asha Rao | |
| Mobile | Us | +91 98765 43210 | Stored as text |
| Address Line 1 | Us | 12 MG Road | |
| Address Line 2 | Us | Flat 4B | May be blank |
| Landmark | Us | Near the metro | May be blank |
| City | Us | Bengaluru | |
| State | Us | Karnataka | |
| PIN Code | Us | 560001 | Stored as text so Excel keeps all 6 digits |
| Country | Us | IN | |
| Product Details | Us | Steel Bottle (P-000002) x2 | Up to 250 characters |
| Quantity | Us | 2 | Total units in the order |
| Payment Mode | Us | COD | |
| COD Amount | Us | 999.00 | Rupees to collect; 0.00 for prepaid orders later |
| Declared Value | Us | 999.00 | Order total in rupees |
| Delivery Instructions | Us | Call before arriving | |
| **AWB No** | Courier | DTDC12345 | Tracking number |
| **Courier Status** | Courier | Out For Delivery | Pick from the dropdown (list below) |
| **Status Date** | Courier | 15-11-2026 10:30 | IST, `DD-MM-YYYY HH:MM`. Blank means "when we import it". |

## Sheet 2: How to fill

The same instructions in plain words for the courier, plus the status list.

## Courier Status words

These words appear in the dropdown:

| Courier writes | Order becomes | Meaning |
| --- | --- | --- |
| Picked Up | Dispatched | Collected from us |
| In Transit | In transit | Moving between hubs |
| Out For Delivery | Out for delivery | With the delivery agent today |
| Delivered | Delivered (COD marked paid) | Handed to the customer |
| Undelivered | Delivery failed | Attempt failed; will retry or return |
| RTO In Transit | Returning | Coming back to us |
| RTO Delivered | Returned | Returned to us |

The import also accepts common variants, case-insensitively: Dispatched, Shipped, Pickup Done,
Reached Hub, OFD, Delivery Failed, NDR, RTO, Return In Transit, Returned. Any other word shows up as
a problem in the preview, and nothing is changed for that row.

## What the import does with each row

- **Will update:** the status moves forward and/or a new AWB is saved.
- **No change:** the order is already at that status, or already further along. This happens when
  the courier resends yesterday's rows.
- **Problem:** the reason is shown. Examples: unknown order number, unknown status word, an order
  not handed over yet, or a step the order lifecycle doesn't allow (such as Delivered after
  Cancelled).

Applying is all-or-nothing per file and can only happen once. Rows are re-checked against the
current orders at that moment. Uploading the same file again changes nothing.

The import also accepts other header names for the key columns: Order No / Order Number /
Reference No; AWB No / Tracking Number / Waybill; Courier Status / Status / Shipment Status;
Status Date / Date / Updated At. A courier's own report often works without any change.

## Changing the format later

| To change | Edit |
| --- | --- |
| Export columns (names, order, which ones) | `COLUMNS` in `backend/app/modules/dispatch/excel.py` |
| Header names the import recognises | `HEADER_ALIASES` in `backend/app/modules/courier_import/parser.py` |
| Status words and what they map to | `CANONICAL_STATUS_WORDS` (dropdown) and `STATUS_WORDS` (accepted) in the same file |
| Date formats accepted | `_DATE_FORMATS` in the same file |

If the courier's template is a different shape altogether, `COLUMNS` can be rewritten to match it.
Tests in `backend/tests/test_dispatch.py` and `backend/tests/test_courier_import.py` (including an
export-then-import round trip) show whether everything still fits together.
