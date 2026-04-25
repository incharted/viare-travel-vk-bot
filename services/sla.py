from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime

from vkbottle.bot import Bot

from services.admin import add_log
from services.notifications import notify_managers
from services.requests import list_requests_for_sla, mark_sla_reminder_sent, request_status_label

logger = logging.getLogger(__name__)

SLA_THRESHOLDS_MINUTES = (15, 30, 60)
SLA_CHECK_INTERVAL_SECONDS = 60


def _minutes_since(iso_timestamp: str | None) -> int:
    if not iso_timestamp:
        return 0
    try:
        moment = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 0
    now = datetime.now(moment.tzinfo) if moment.tzinfo else datetime.now()
    delta = now - moment
    return max(int(delta.total_seconds() // 60), 0)


def _format_sla_message(request: dict, threshold: int) -> str:
    destination = request.get("destination") or request.get("country") or "не указано"
    budget = request.get("budget")
    budget_text = f"{int(budget):,} ₽".replace(",", " ") if isinstance(budget, int) and budget > 0 else "не указан"
    return (
        f"⏰ SLA {threshold} мин: заявка #{request['id']} без ответа клиенту.\n"
        f"Статус: {request_status_label(str(request.get('status') or ''))}\n"
        f"Клиент: vk={request['vk_id']}\n"
        f"Направление: {destination}\n"
        f"Бюджет: {budget_text}\n"
        "Действие: откройте карточку /request_card или возьмите заявку /request_assign."
    )


async def _notify_assigned_manager(bot: Bot, manager_vk_id: int, text: str) -> bool:
    try:
        await bot.api.messages.send(
            user_id=manager_vk_id,
            message=text,
            random_id=random.randint(1, 2_000_000_000),
        )
        return True
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to send SLA reminder to assigned manager %s: %s", manager_vk_id, err)
        return False


async def check_sla_reminders(bot: Bot) -> None:
    rows = await list_requests_for_sla(limit=300)
    if not rows:
        return

    for request in rows:
        minutes = _minutes_since(str(request.get("created_at") or ""))
        if minutes <= 0:
            continue

        for threshold in SLA_THRESHOLDS_MINUTES:
            if minutes < threshold:
                continue
            flag = request.get(f"sla_{threshold}_sent")
            if int(flag or 0) == 1:
                continue

            text = _format_sla_message(request, threshold)
            assigned_manager_vk_id = request.get("assigned_manager_vk_id")
            sent = False
            if assigned_manager_vk_id:
                sent = await _notify_assigned_manager(bot, int(assigned_manager_vk_id), text)
            if not sent:
                await notify_managers(bot, text)

            await mark_sla_reminder_sent(int(request["id"]), threshold)
            await add_log(
                None,
                "sla_reminder_sent",
                f"request_id={request['id']}; threshold={threshold}; assigned={assigned_manager_vk_id or '-'}",
            )


def start_sla_worker(loop: asyncio.AbstractEventLoop, bot: Bot) -> None:
    async def _runner() -> None:
        # Give bot a short warm-up before first pass.
        await asyncio.sleep(20)
        while True:
            try:
                await check_sla_reminders(bot)
            except Exception:  # noqa: BLE001
                logger.exception("SLA worker iteration failed")
            await asyncio.sleep(SLA_CHECK_INTERVAL_SECONDS)

    loop.create_task(_runner())
