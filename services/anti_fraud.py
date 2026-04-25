from __future__ import annotations

import re
import time
from collections import defaultdict, deque

URL_RE = re.compile(r"(https?://|www\.)", re.IGNORECASE)
REPEATED_CHAR_RE = re.compile(r"(.)\1{11,}")


class InMemoryAntiFraud:
    def __init__(self) -> None:
        self._rate_violations: dict[int, deque[float]] = defaultdict(deque)
        self._same_message_events: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    @staticmethod
    def inspect_text(text: str) -> str | None:
        content = (text or "").strip()
        if not content:
            return None

        links_count = len(URL_RE.findall(content))
        if links_count >= 3:
            return "many_links"
        if len(content) >= 600 and links_count >= 1:
            return "long_text_with_links"
        if REPEATED_CHAR_RE.search(content.lower()):
            return "repeated_symbols"
        if content.count("\n") >= 20:
            return "flood_newlines"
        return None

    def register_same_message(self, user_id: int, text: str, window_sec: int = 45) -> str | None:
        normalized = " ".join((text or "").strip().lower().split())
        if not normalized:
            return None
        key = (user_id, normalized[:300])
        now = time.monotonic()
        bucket = self._same_message_events[key]
        while bucket and now - bucket[0] > window_sec:
            bucket.popleft()
        bucket.append(now)
        if len(bucket) >= 5:
            return "repeated_same_message"
        return None

    def register_rate_violation(self, user_id: int, window_sec: int = 180) -> int:
        now = time.monotonic()
        bucket = self._rate_violations[user_id]
        while bucket and now - bucket[0] > window_sec:
            bucket.popleft()
        bucket.append(now)
        return len(bucket)


anti_fraud = InMemoryAntiFraud()
