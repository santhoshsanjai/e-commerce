from datetime import timedelta, timezone

# ADR 0006: India only for v1. IST has no daylight saving, so a fixed offset is exact.
IST = timezone(timedelta(hours=5, minutes=30), "IST")
