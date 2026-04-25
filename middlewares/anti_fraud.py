from __future__ import annotations

import logging

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from config import get_settings
from services.admin import add_log
from services.anti_fraud import anti_fraud
from services.users import (
    increment_spam_strike,
    is_user_blocked,
    set_user_block,
    upsert_user,
)

logger = logging.getLogger(__name__)

AUTO_BLOCK_THRESHOLD = 4
AUTO_BLOCK_DURATION_MIN = 30


class AntiFraudMiddleware(BaseMiddleware[Message]):
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
                "Ваш аккаунт временно ограничен из-за подозрительной активности.\n"
                f"Причина: {reason or 'anti_spam'}{until_text}.\n"
                "Если это ошибка, обратитесь к менеджеру VIARE Travel."
            )
            self.stop("user_blocked")
            return

        text = self.event.text or ""
        suspicious_reason = anti_fraud.inspect_text(text) or anti_fraud.register_same_message(self.event.from_id, text)
        if not suspicious_reason:
            return

        strikes = await increment_spam_strike(self.event.from_id)
        await add_log(
            user_id=user_id,
            event_type="anti_fraud_strike",
            message=f"reason={suspicious_reason}; strikes={strikes}",
            level="WARNING",
        )

        if strikes >= AUTO_BLOCK_THRESHOLD:
            await set_user_block(
                self.event.from_id,
                True,
                reason=f"auto_block:{suspicious_reason}",
                duration_min=AUTO_BLOCK_DURATION_MIN,
            )
            logger.warning("User %s auto-blocked by anti-fraud middleware", self.event.from_id)
            await self.event.answer(
                "Обнаружена подозрительная активность. "
                f"Доступ временно ограничен на {AUTO_BLOCK_DURATION_MIN} минут."
            )
            self.stop("user_auto_blocked")
