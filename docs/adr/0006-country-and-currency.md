# ADR 0006: One country and currency (India, INR)

**Status:** Provisional · 2026-11-14 · answers handoff question 9

## Context
The handoff mentions paise and GST, which suggests India. Not yet confirmed.

## Decision
First release: one country (IN), one currency (INR), English only. Money is stored as integer minor units
(paise) with an explicit currency column on every priced row, so a second currency needs no schema change.
All timestamps are stored in UTC and displayed in the user's time zone (default Asia/Kolkata).
Addresses use generic fields (line 1, line 2, landmark, city, region, postal code, country code).

## What changes if revisited
A different single country changes defaults and the postal-code validator. Multiple currencies need
per-currency prices and a currency selector (high effort once orders exist).
