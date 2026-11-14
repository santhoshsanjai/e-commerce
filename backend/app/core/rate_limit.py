import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """In-process sliding-window limiter.

    Good enough for a single API instance. Replace with a shared store (e.g. Redis) before running
    more than one instance in production; tracked in the Phase 5 hardening work.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record an attempt; return False when the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


login_limiter = SlidingWindowLimiter()
