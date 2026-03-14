from __future__ import annotations

import re

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

PLAIN_PREFIXES = (
    "VIARE Travel консультант",
    "VIARE Travel",
)

MENTION_PREFIX_RE = re.compile(r"^\[[^\]]+\|[^\]]+\]\s*")


class TextNormalizeMiddleware(BaseMiddleware[Message]):
    async def pre(self) -> None:
        text = (self.event.text or "").strip()
        if not text:
            return

        normalized = MENTION_PREFIX_RE.sub("", text).strip()
        for prefix in PLAIN_PREFIXES:
            prefix_with_space = f"{prefix} "
            if normalized.startswith(prefix_with_space):
                normalized = normalized[len(prefix_with_space) :].strip()
                break

        self.event.text = normalized
