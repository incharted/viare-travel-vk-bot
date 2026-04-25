from __future__ import annotations

import logging

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from config import get_settings
from services.admin import add_log
from services.anti_fraud import anti_fraud
from services.rate_limiter import rate_limiter
from services.users import is_user_blocked, set_user_block, upsert_user

logger = logging.getLogger(__name__)

RATE_LIMIT_AUTO_BLOCK_THRESHOLD = 6
RATE_LIMIT_AUTO_BLOCK_MIN = 20


class RateLimitMiddleware(BaseMiddleware[Message]):
    async def pre(self) -> None:
        if self.event.from_id is None or self.event.from_id <= 0:
            return

        settings = get_settings()
        if self.event.from_id in settings.admin_ids:
            return

        user_id = await upsert_user(self.event.from_id)
        blocked, reason, blocked_until = await is_user_blocked(self.event.from_id)
        if blocked:
            until_text = f" до {blocked_until}" if blocked_until else ""
            await self.event.answer(
                "Ваш аккаунт временно ограничен антиспам-системой.\n"
                f"Причина: {reason or 'rate_limit'}{until_text}."
            )
            self.stop("user_blocked")
            return

        allowed = rate_limiter.allow(
            user_id=self.event.from_id,
            max_events=settings.rate_limit_count,
            window_sec=settings.rate_limit_window_sec,
        )
        if not allowed:
            logger.warning("Rate limit exceeded for user %s", self.event.from_id)
            violations = anti_fraud.register_rate_violation(self.event.from_id)
            await add_log(
                user_id=user_id,
                event_type="rate_limit_exceeded",
                message=f"violations={violations}",
                level="WARNING",
            )
            if violations >= RATE_LIMIT_AUTO_BLOCK_THRESHOLD:
                await set_user_block(
                    self.event.from_id,
                    True,
                    reason="auto_block:rate_limit",
                    duration_min=RATE_LIMIT_AUTO_BLOCK_MIN,
                )
                await self.event.answer(
                    "Слишком много запросов за короткое время.\n"
                    f"Доступ временно ограничен на {RATE_LIMIT_AUTO_BLOCK_MIN} минут."
                )
                self.stop("rate_limit_auto_blocked")
                return
            await self.event.answer(
                "Слишком много запросов. Подождите несколько секунд и попробуйте снова."
            )
            self.stop("rate_limited")
