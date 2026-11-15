# 0008: Our own courier Excel format

- **Status:** Provisional (the owner asked us to define it now and change it when a courier is chosen)
- **Date:** 2026-11-14

## Context

Orders go to the courier as an Excel file, and the courier's status updates come back as Excel
(handoff: no courier API in v1). We don't have a courier's template yet.

## Decision

- One round-trip sheet. The dispatch export has the shipping columns plus three blank columns the
  courier fills: **AWB No**, **Courier Status**, **Status Date**. The courier sends the same file
  back and we import it.
- `Order No` is the key. Status words come from a short fixed list, offered as a dropdown, with
  common variants also accepted. Dates are IST, `DD-MM-YYYY HH:MM`.
- Imports are previewed, then applied once. They are idempotent and follow the order lifecycle map.
- The full format is in [docs/courier-file-format.md](../courier-file-format.md).

## Consequences

- We can run dispatch end to end now with any courier willing to fill a sheet.
- Export columns, accepted headers and status words live in code tables, not the database. A change
  is a small PR with tests, not a migration.

## What changes if revisited

When a courier is chosen, map its template in `COLUMNS` (export) and its report headers and status
words in `HEADER_ALIASES` / `STATUS_WORDS` (import). This is roughly half a day including tests.
Making this editable from the admin portal would be a larger feature and is not planned for v1.
