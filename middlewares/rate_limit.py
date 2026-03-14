from __future__ import annotations

import logging

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from config import get_settings
from services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware[Message]):
    async def pre(self) -> None:
        if self.event.from_id is None or self.event.from_id <= 0:
            return

        settings = get_settings()
        if self.event.from_id in settings.admin_ids:
            return

        allowed = rate_limiter.allow(
            user_id=self.event.from_id,
            max_events=settings.rate_limit_count,
            window_sec=settings.rate_limit_window_sec,
        )
        if not allowed:
            logger.warning("Rate limit exceeded for user %s", self.event.from_id)
            await self.event.answer(
                "Слишком много запросов. Подождите несколько секунд и попробуйте снова."
            )
            self.stop("rate_limited")
