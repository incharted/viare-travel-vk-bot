from __future__ import annotations

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int, max_events: int, window_sec: int) -> bool:
        now = time.monotonic()
        bucket = self._events[user_id]

        while bucket and now - bucket[0] > window_sec:
            bucket.popleft()

        if len(bucket) >= max_events:
            return False

        bucket.append(now)
        return True


rate_limiter = InMemoryRateLimiter()
