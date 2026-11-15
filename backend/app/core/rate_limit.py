"""Login rate limiting, stored in PostgreSQL so every API instance shares the same counts.

Each attempt is recorded before the password is checked, atomically with the limit check (an
advisory lock per key serialises concurrent attempts, so firing requests in parallel can't slip
past the limit). A successful attempt then deletes its own records, so only failures count.
"""

import random
import zlib
from dataclasses import dataclass, field

from sqlalchemy import text

from app.infrastructure.database import engine

# Old rows are removed per key on every check; this sweeps keys that are never seen again.
_SWEEP_PROBABILITY = 0.01


@dataclass
class Attempt:
    """Hits recorded for one attempt, so a success can remove exactly these."""

    hit_ids: list[int] = field(default_factory=list)


class PostgresLimiter:
    def hit(self, key: str, limit: int, window_seconds: int, attempt: Attempt) -> bool:
        """Record an attempt for `key`; return False (recording nothing) when over the limit."""
        with engine.begin() as conn:
            conn.execute(
                text("SELECT pg_advisory_xact_lock(:lock)"),
                {"lock": zlib.crc32(key.encode()) - 2**31},
            )
            conn.execute(
                text(
                    "DELETE FROM rate_limit_hits WHERE key = :key "
                    "AND hit_at <= now() - make_interval(secs => :window)"
                ),
                {"key": key, "window": window_seconds},
            )
            count = conn.scalar(
                text("SELECT count(*) FROM rate_limit_hits WHERE key = :key"), {"key": key}
            )
            if (count or 0) >= limit:
                return False
            hit_id = conn.scalar(
                text("INSERT INTO rate_limit_hits (key) VALUES (:key) RETURNING id"), {"key": key}
            )
            attempt.hit_ids.append(int(hit_id))
            if random.random() < _SWEEP_PROBABILITY:  # noqa: S311 - not security sensitive
                conn.execute(
                    text("DELETE FROM rate_limit_hits WHERE hit_at < now() - interval '1 day'")
                )
        return True

    def forget(self, attempt: Attempt) -> None:
        """Remove the hits of a successful attempt."""
        if not attempt.hit_ids:
            return
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM rate_limit_hits WHERE id = ANY(:ids)"), {"ids": attempt.hit_ids}
            )
        attempt.hit_ids.clear()

    def reset(self, key: str | None = None) -> None:
        with engine.begin() as conn:
            if key is None:
                conn.execute(text("DELETE FROM rate_limit_hits"))
            else:
                conn.execute(text("DELETE FROM rate_limit_hits WHERE key = :key"), {"key": key})


login_limiter = PostgresLimiter()
