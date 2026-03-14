from __future__ import annotations

import logging

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from config import get_settings
from services.admin import add_log
from services.users import upsert_user

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseMiddleware[Message]):
    async def pre(self) -> None:
        if self.event.from_id is None or self.event.from_id <= 0:
            return

        try:
            settings = get_settings()
            is_admin = self.event.from_id in settings.admin_ids
            is_manager = self.event.from_id in settings.manager_ids
            user_id = await upsert_user(self.event.from_id, is_admin=is_admin, is_manager=is_manager)

            text = (self.event.text or "").strip()
            await add_log(
                user_id=user_id,
                event_type="message_received",
                message=text[:2000],
                level="INFO",
            )
        except Exception as err:  # noqa: BLE001
            logger.exception("Audit middleware failed: %s", err)
