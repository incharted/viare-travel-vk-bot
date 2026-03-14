from __future__ import annotations

import logging

from vkbottle.bot import Bot, BotLabeler, Message

from keyboards.main_menu import get_main_menu_keyboard, get_welcome_keyboard
from services.admin import add_log
from services.content import get_content_block
from services.notifications import notify_managers
from services.requests import create_request
from services.tours import list_tours
from services.users import get_user_by_vk_id, upsert_user
from utils.formatting import build_tour_catalog_messages, format_request_notification

logger = logging.getLogger(__name__)


async def _ensure_user(message: Message) -> int:
    user = await get_user_by_vk_id(message.from_id)
    if user:
        return int(user["id"])
    return await upsert_user(message.from_id)


def register_common_handlers(labeler: BotLabeler, bot: Bot) -> None:
    @labeler.message(text=["/myid", "/whoami"])
    async def my_id_handler(message: Message) -> None:
        await _ensure_user(message)
        await message.answer(
            f"Ваш VK ID: {message.from_id}\n"
            "Если хотите получить доступ к админ-командам, добавьте этот ID в ADMIN_IDS в .env и перезапустите бота."
        )

    @labeler.message(text=["/start", "Начать", "start", "Start"])
    async def start_handler(message: Message) -> None:
        await _ensure_user(message)
        await message.answer(
            await get_content_block("welcome"),
            keyboard=get_welcome_keyboard(),
        )

    @labeler.message(text=["Что умеет бот?", "Меню", "/menu", "Привет", "Здравствуйте", "Добрый день"])
    async def welcome_details_handler(message: Message) -> None:
        await _ensure_user(message)
        await message.answer(await get_content_block("welcome_details"), keyboard=get_main_menu_keyboard())

    @labeler.message(text="Услуги VIARE Travel")
    async def services_handler(message: Message) -> None:
        await message.answer(await get_content_block("services"), keyboard=get_main_menu_keyboard())

    @labeler.message(text="О VIARE Travel")
    async def about_handler(message: Message) -> None:
        await message.answer(await get_content_block("about"), keyboard=get_main_menu_keyboard())

    @labeler.message(text="FAQ")
    async def faq_handler(message: Message) -> None:
        await message.answer(await get_content_block("faq"), keyboard=get_main_menu_keyboard())

    @labeler.message(text="Контакты")
    async def contacts_handler(message: Message) -> None:
        await message.answer(await get_content_block("contacts"), keyboard=get_main_menu_keyboard())

    @labeler.message(text="Оплата и бронирование")
    async def payment_handler(message: Message) -> None:
        await message.answer(await get_content_block("payment"), keyboard=get_main_menu_keyboard())

    @labeler.message(text=["Все туры", "/tours", "Каталог туров"])
    async def all_tours_handler(message: Message) -> None:
        tours = await list_tours(1000)
        if not tours:
            await message.answer(
                "Сейчас активных туров нет. Нажмите «Связаться с менеджером», и VIARE Travel подберет вариант вручную.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        for index, catalog_message in enumerate(build_tour_catalog_messages(tours)):
            keyboard = get_main_menu_keyboard() if index == 0 else None
            await message.answer(catalog_message, keyboard=keyboard)

    @labeler.message(text="Связаться с менеджером")
    async def manager_handler(message: Message) -> None:
        user_id = await _ensure_user(message)
        request_id = await create_request(
            user_id=user_id,
            travel_scope=None,
            country=None,
            destination=None,
            budget=None,
            travelers=None,
            start_date=None,
            end_date=None,
            rest_type=None,
            manager_required=True,
        )
        await add_log(user_id, "manager_requested", "User asked manager contact")
        await notify_managers(
            bot,
            format_request_notification(
                request_id=request_id,
                user_vk_id=message.from_id,
                travel_scope=None,
                country=None,
                destination=None,
                budget=None,
                travelers=None,
                start_date=None,
                end_date=None,
                rest_type=None,
                manager_required=True,
            ),
        )
        await message.answer(
            "Передал запрос менеджеру VIARE Travel. С вами свяжутся в ближайшее время.",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message()
    async def fallback_handler(message: Message) -> None:
        text = (message.text or "").strip()
        if text.startswith("/"):
            await message.answer("Неизвестная команда. Напишите /menu для открытия меню.")
            return

        logger.debug("Fallback triggered for message: %s", text)
        if message.peer_id >= 2_000_000_000:
            await message.answer(
                "Если вы пишете в общем чате, нажимайте кнопки меню или откройте личные сообщения сообщества.\n"
                "Для старта можно написать /menu.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        await message.answer(
            "Не понял запрос. Используйте кнопки меню или напишите /menu.",
            keyboard=get_main_menu_keyboard(),
        )
