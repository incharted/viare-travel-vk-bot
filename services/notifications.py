from __future__ import annotations

import logging
import random

from vkbottle.bot import Bot

from config import get_settings
from services.users import list_admin_vk_ids, list_manager_vk_ids

logger = logging.getLogger(__name__)


async def notify_managers(bot: Bot, text: str) -> None:
    settings = get_settings()
    recipients = set(settings.admin_ids)
    recipients.update(settings.manager_ids)
    recipients.update(await list_admin_vk_ids())
    recipients.update(await list_manager_vk_ids())

    for vk_id in recipients:
        try:
            await bot.api.messages.send(
                user_id=vk_id,
                message=text,
                random_id=random.randint(1, 2_000_000_000),
            )
        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to notify manager %s: %s", vk_id, err)
