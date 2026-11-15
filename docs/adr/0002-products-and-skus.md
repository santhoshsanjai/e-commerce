# ADR 0002: Every product has SKUs (variants-ready)

**Status:** Provisional · 2026-11-14 · answers handoff question 1

## Context
It is not yet confirmed whether products have variants (size, colour, model). Adding variants after
orders exist is expensive if price and stock live on the product row.

## Decision
Model `product_skus` from the first catalogue migration. Price, compare-at price, currency and stock
live on the SKU. In v1 every product is created with exactly one default SKU and the admin UI hides
variant options. Order lines reference the SKU and snapshot product number, name and SKU code.

## Consequences
One extra join in catalogue queries. Turning on variants later is a UI change plus an `option_values`
field, with no data migration of existing orders.

## What changes if revisited
If variants are confirmed: add option definitions per category and a variant picker on the product page.
If simple products are confirmed: nothing changes.
