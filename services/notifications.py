from __future__ import annotations

import logging
import random

from vkbottle.bot import Bot

from config import get_settings
from services.users import list_admin_vk_ids, list_manager_vk_ids

logger = logging.getLogger(__name__)


async def collect_admin_recipients() -> set[int]:
    settings = get_settings()
    recipients = set(settings.admin_ids)
    recipients.update(await list_admin_vk_ids())
    return recipients


async def collect_manager_recipients() -> set[int]:
    settings = get_settings()
    recipients = set(settings.manager_ids)
    recipients.update(await list_manager_vk_ids())
    return recipients


async def collect_staff_recipients() -> set[int]:
    recipients = await collect_admin_recipients()
    recipients.update(await collect_manager_recipients())
    return recipients


async def notify_recipients(bot: Bot, text: str, recipients: set[int]) -> None:
    for vk_id in recipients:
        try:
            await bot.api.messages.send(
                user_id=vk_id,
                message=text,
                random_id=random.randint(1, 2_000_000_000),
            )
        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to notify vk=%s: %s", vk_id, err)


async def notify_managers(bot: Bot, text: str) -> None:
    recipients = await collect_staff_recipients()
    await notify_recipients(bot, text, recipients)


async def notify_assigned_manager(bot: Bot, text: str, manager_vk_id: int | None) -> None:
    recipients = await collect_admin_recipients()
    if manager_vk_id:
        recipients.add(int(manager_vk_id))

    if not recipients:
        recipients = await collect_staff_recipients()
    await notify_recipients(bot, text, recipients)
