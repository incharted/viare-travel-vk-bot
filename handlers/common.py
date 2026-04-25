from __future__ import annotations

import logging

from vkbottle.bot import Bot, BotLabeler, Message

from keyboards.main_menu import get_main_menu_keyboard, get_staff_menu_keyboard
from services.admin import add_log
from services.assignment import auto_assign_request
from services.auth import get_staff_role, is_admin, is_manager
from services.content import get_content_block
from services.favorites import add_favorite_tour, count_favorite_tours, list_favorite_tours, remove_favorite_tour
from services.notifications import notify_assigned_manager
from services.requests import (
    create_request,
    get_latest_request_by_user_id,
    list_requests_by_user_id,
    request_status_label,
)
from services.tours import get_tour_by_id, list_tours
from services.users import get_user_by_vk_id, upsert_user
from utils.formatting import build_tour_catalog_messages, format_request_notification
from utils.states import ClientState

logger = logging.getLogger(__name__)

CLIENT_ESCAPE_TEXTS = {"в меню", "меню", "/menu", "/start", "start", "начать", "отмена", "cancel"}
FORCED_CLIENT_MODE_PEERS: set[int] = set()


def _is_forced_client_mode(peer_id: int) -> bool:
    return peer_id in FORCED_CLIENT_MODE_PEERS


def _format_price(value: int | None) -> str:
    if value is None:
        return "не указан"
    return f"{value:,}".replace(",", " ")


def _scope_label(value: str | None) -> str:
    if value == "domestic":
        return "По России"
    if value == "abroad":
        return "За границу"
    return "Не указан"


def _request_short_line(request: dict) -> str:
    destination = request.get("destination") or request.get("country") or "не указано"
    budget = f"{_format_price(request.get('budget'))} ₽" if request.get("budget") else "не указан"
    date_text = f"{request.get('start_date') or '-'} - {request.get('end_date') or '-'}"
    return (
        f"#{request['id']} | {request_status_label(str(request.get('status') or ''))} | "
        f"{destination} | бюджет: {budget} | даты: {date_text}"
    )


def _favorite_line(index: int, tour: dict) -> str:
    destination = tour.get("destination") or tour.get("country") or "не указано"
    return (
        f"{index}. [ID {tour.get('id')}] {tour.get('name')}\n"
        f"   {destination} | {tour.get('duration_days')} дн. | от {_format_price(int(tour.get('price_per_person') or 0))} ₽/чел."
    )


async def _ensure_user(message: Message) -> int:
    user = await get_user_by_vk_id(message.from_id)
    if user:
        return int(user["id"])
    return await upsert_user(message.from_id)


async def _handle_client_state_escape(bot: Bot, message: Message) -> bool:
    text = (message.text or "").strip().lower()
    if text in CLIENT_ESCAPE_TEXTS:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Процесс выполнен. Возвращаю в главное меню.", keyboard=get_main_menu_keyboard())
        return True
    return False


def _user_home_text() -> str:
    return (
        "VIARE Travel\n"
        "Помогу быстро подобрать тур и не запутаться в шагах.\n\n"
        "Что можно сделать сейчас:\n"
        "1. Нажать «Подобрать тур» и пройти короткий мастер.\n"
        "2. Нажать «Все туры» и посмотреть весь каталог.\n"
        "3. Нажать «Связаться с менеджером» для живой консультации.\n"
        "4. Следить за заявками через «Мои заявки» и «Мой статус».\n"
        "5. Сохранять варианты в «Избранное».\n\n"
        "Подсказка: в любой момент нажмите «В меню»."
    )


def _manager_home_text() -> str:
    return (
        "Режим менеджера VIARE Travel\n"
        "Вы можете брать заявки, отвечать клиентам и работать по шаблонам.\n\n"
        "Быстрый старт:\n"
        "- Открыть список: /requests\n"
        "- Взять следующую: /request_next\n"
        "- Закрепить за собой: /request_assign\n"
        "- Шпаргалка по действиям: /manager_help"
    )


def _admin_home_text() -> str:
    return (
        "Режим администратора VIARE Travel\n"
        "Доступны управление менеджерами, аналитика, контент и каталог туров.\n\n"
        "Быстрый старт:\n"
        "- Панель заявок: /requests\n"
        "- Аналитика: /stats\n"
        "- Менеджеры: /managers\n"
        "- Полная шпаргалка: /admin_help"
    )


async def _send_role_home(message: Message) -> None:
    if _is_forced_client_mode(message.peer_id):
        await message.answer(
            "Режим клиента активен.\n"
            "Вы можете пользоваться ботом как обычный пользователь.\n"
            "Чтобы вернуть панель сотрудника, напишите /staff_mode.",
            keyboard=get_main_menu_keyboard(),
        )
        return

    role = await get_staff_role(message.from_id)
    if role == "admin":
        await message.answer(_admin_home_text(), keyboard=get_staff_menu_keyboard("admin"))
        return
    if role == "manager":
        await message.answer(_manager_home_text(), keyboard=get_staff_menu_keyboard("manager"))
        return

    await message.answer(_user_home_text(), keyboard=get_main_menu_keyboard())


def register_common_handlers(labeler: BotLabeler, bot: Bot) -> None:
    @labeler.message(text=["/myid", "/whoami"])
    async def my_id_handler(message: Message) -> None:
        await _ensure_user(message)
        admin_flag = await is_admin(message.from_id)
        manager_flag = await is_manager(message.from_id)
        if admin_flag:
            role_text = "администратор"
        elif manager_flag:
            role_text = "менеджер"
        else:
            role_text = "клиент"
        await message.answer(
            f"Ваш VK ID: {message.from_id}\n"
            f"Текущая роль: {role_text}\n\n"
            "Если хотите доступ к админ-командам:\n"
            "1. Добавьте этот ID в ADMIN_IDS в .env\n"
            "2. Перезапустите бота\n"
            "3. Напишите /role и проверьте, что роль обновилась"
        )

    @labeler.message(text=["/role", "Моя роль"])
    async def role_handler(message: Message) -> None:
        await _ensure_user(message)
        admin_flag = await is_admin(message.from_id)
        manager_flag = await is_manager(message.from_id)
        if admin_flag:
            await message.answer(
                "Роль: администратор.\n"
                "Доступны команды /admin, /admin_help, /managers, /manager_add, /stats и другие."
            )
            return
        if manager_flag:
            await message.answer(
                "Роль: менеджер.\n"
                "Доступны команды /staff, /manager_help, /requests, /reply_request."
            )
            return
        await message.answer(
            "Роль: клиент.\n"
            "Для получения прав передайте ваш VK ID администратору.\n"
            "Ваш ID можно посмотреть командой /myid."
        )

    @labeler.message(text=["/client_mode", "Режим клиента"])
    async def client_mode_handler(message: Message) -> None:
        await _ensure_user(message)
        role = await get_staff_role(message.from_id)
        if not role:
            await message.answer("Вы уже в пользовательском режиме.", keyboard=get_main_menu_keyboard())
            return
        FORCED_CLIENT_MODE_PEERS.add(message.peer_id)
        await message.answer(
            "Включил режим клиента.\n"
            "Теперь в этом чате вы видите обычное пользовательское меню.\n"
            "Чтобы вернуть панель сотрудника, напишите /staff_mode.",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(text=["/staff_mode", "Режим панели"])
    async def staff_mode_handler(message: Message) -> None:
        await _ensure_user(message)
        role = await get_staff_role(message.from_id)
        if not role:
            await message.answer("У вас нет роли сотрудника, остается пользовательский режим.")
            return
        FORCED_CLIENT_MODE_PEERS.discard(message.peer_id)
        await message.answer(
            "Режим панели включен.",
            keyboard=get_staff_menu_keyboard(role),
        )

    @labeler.message(text=["/start", "Начать", "start", "Start"])
    async def start_handler(message: Message) -> None:
        await _ensure_user(message)
        await _send_role_home(message)

    @labeler.message(text=["Что умеет бот?", "Меню", "/menu", "Привет", "Здравствуйте", "Добрый день"])
    async def welcome_details_handler(message: Message) -> None:
        await _ensure_user(message)
        role = None if _is_forced_client_mode(message.peer_id) else await get_staff_role(message.from_id)
        if role:
            await _send_role_home(message)
            return
        await message.answer(await get_content_block("welcome_details"), keyboard=get_main_menu_keyboard())

    @labeler.message(text=["Как пользоваться", "/help", "Помощь"])
    async def help_handler(message: Message) -> None:
        await _ensure_user(message)
        role = None if _is_forced_client_mode(message.peer_id) else await get_staff_role(message.from_id)
        if role == "admin":
            await message.answer(
                "Вы в режиме администратора.\n"
                "Нажмите /admin для панели, /admin_help для полной подсказки.\n"
                "Быстрый гайд по менеджерам: /manager_howto",
            )
            return
        if role == "manager":
            await message.answer(
                "Вы в режиме менеджера.\n"
                "Нажмите /staff для панели, /manager_help для полной подсказки.",
            )
            return
        await message.answer(
            "Как пользоваться ботом:\n"
            "1. Нажмите «Подобрать тур».\n"
            "2. Пройдите 6 коротких шагов.\n"
            "3. Нажмите «Подтверждаю», чтобы отправить заявку.\n\n"
            "Личный кабинет клиента:\n"
            "- «Мои заявки» — список ваших заявок\n"
            "- «Мой статус» — последняя заявка и текущий этап\n"
            "- «Избранное» — сохраненные туры",
            keyboard=get_main_menu_keyboard(),
        )

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

    @labeler.message(text=["Мои заявки", "/my_requests"])
    async def my_requests_handler(message: Message) -> None:
        user_id = await _ensure_user(message)
        requests = await list_requests_by_user_id(user_id, limit=10)
        if not requests:
            await message.answer(
                "У вас пока нет заявок.\n"
                "Нажмите «Подобрать тур», чтобы создать первую.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        lines = ["Ваши последние заявки:", ""]
        lines.extend(_request_short_line(item) for item in requests)
        lines.extend(
            [
                "",
                "Подсказка:",
                "- «Мой статус» покажет подробности по последней заявке.",
            ]
        )
        await message.answer("\n".join(lines), keyboard=get_main_menu_keyboard())

    @labeler.message(text=["Мой статус", "/my_status"])
    async def my_status_handler(message: Message) -> None:
        user_id = await _ensure_user(message)
        request = await get_latest_request_by_user_id(user_id)
        if not request:
            await message.answer(
                "Пока нет активной заявки.\n"
                "Запустите подбор тура кнопкой «Подобрать тур».",
                keyboard=get_main_menu_keyboard(),
            )
            return

        destination = request.get("destination") or request.get("country") or "не указано"
        assignee = request.get("assigned_manager_vk_id")
        assignee_text = "менеджер уже назначен" if assignee else "назначается автоматически"
        await message.answer(
            "Последняя заявка:\n"
            f"- ID: #{request['id']}\n"
            f"- Статус: {request_status_label(str(request.get('status') or ''))}\n"
            f"- Формат: {_scope_label(str(request.get('travel_scope') or ''))}\n"
            f"- Направление: {destination}\n"
            f"- Ответственный менеджер: {assignee_text}\n"
            f"- Обновлена: {request.get('updated_at') or request.get('created_at')}",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(text=["Избранное", "/favorites"])
    async def favorites_handler(message: Message) -> None:
        user_id = await _ensure_user(message)
        favorites = await list_favorite_tours(user_id, limit=15)
        if not favorites:
            await message.answer(
                "Избранное пока пустое.\n"
                "Чтобы добавить тур: /fav\n"
                "Чтобы удалить тур: /unfav",
                keyboard=get_main_menu_keyboard(),
            )
            return

        lines = ["Ваше избранное:", ""]
        lines.extend(_favorite_line(index, tour) for index, tour in enumerate(favorites, start=1))
        lines.extend(
            [
                "",
                "Команды:",
                "/fav — добавить тур по ID",
                "/unfav — удалить тур по ID",
                "/compare_favorites — сравнить до 3 сохраненных туров",
            ]
        )
        await message.answer("\n".join(lines), keyboard=get_main_menu_keyboard())

    @labeler.message(text=["/fav", "Добавить в избранное"])
    async def favorite_add_prompt(message: Message) -> None:
        await _ensure_user(message)
        await bot.state_dispenser.set(message.peer_id, ClientState.FAVORITE_ADD)
        await message.answer(
            "Введите ID тура, который нужно добавить в избранное.\nПример: 12",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(state=ClientState.FAVORITE_ADD)
    async def favorite_add_state(message: Message) -> None:
        if await _handle_client_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен числовой ID тура. Пример: 12")
            return

        user_id = await _ensure_user(message)
        tour_id = int(text)
        added = await add_favorite_tour(user_id, tour_id)
        if not added:
            await message.answer(
                "Не нашел активный тур с таким ID. Проверьте каталог и попробуйте еще раз.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        tour = await get_tour_by_id(tour_id)
        total = await count_favorite_tours(user_id)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Тур [ID {tour_id}] «{tour.get('name') if tour else 'без названия'}» добавлен в избранное.\n"
            f"Сейчас в избранном: {total}.",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(text=["/unfav", "Удалить из избранного"])
    async def favorite_remove_prompt(message: Message) -> None:
        await _ensure_user(message)
        await bot.state_dispenser.set(message.peer_id, ClientState.FAVORITE_REMOVE)
        await message.answer(
            "Введите ID тура, который нужно удалить из избранного.\nПример: 12",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(state=ClientState.FAVORITE_REMOVE)
    async def favorite_remove_state(message: Message) -> None:
        if await _handle_client_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен числовой ID тура. Пример: 12")
            return

        user_id = await _ensure_user(message)
        tour_id = int(text)
        removed = await remove_favorite_tour(user_id, tour_id)
        if not removed:
            await message.answer(
                "Такой тур не найден в вашем избранном.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        total = await count_favorite_tours(user_id)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Тур [ID {tour_id}] удален из избранного.\nСейчас в избранном: {total}.",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(text=["/compare_favorites", "Сравнить избранное"])
    async def compare_favorites_handler(message: Message) -> None:
        user_id = await _ensure_user(message)
        favorites = await list_favorite_tours(user_id, limit=3)
        if len(favorites) < 2:
            await message.answer(
                "Для сравнения нужно минимум 2 тура в избранном.\n"
                "Добавьте туры через /fav и повторите команду.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        cheapest = min(favorites, key=lambda item: int(item.get("price_per_person") or 0))
        lines = ["Сравнение избранных туров:", ""]
        for index, tour in enumerate(favorites, start=1):
            destination = tour.get("destination") or tour.get("country") or "не указано"
            lines.append(
                f"{index}. [ID {tour.get('id')}] {tour.get('name')}\n"
                f"   {destination} | {tour.get('duration_days')} дн. | "
                f"{_format_price(int(tour.get('price_per_person') or 0))} ₽/чел. | {tour.get('rest_type')}"
            )

        lines.extend(
            [
                "",
                f"Самый бюджетный вариант: [ID {cheapest.get('id')}] {cheapest.get('name')}.",
            ]
        )
        await message.answer("\n".join(lines), keyboard=get_main_menu_keyboard())

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
        assigned_manager_vk_id = await auto_assign_request(request_id)
        await add_log(
            user_id,
            "manager_requested",
            f"User asked manager contact; request_id={request_id}; assigned={assigned_manager_vk_id}",
        )

        notification_text = format_request_notification(
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
        )
        if assigned_manager_vk_id:
            notification_text += f"\nАвтораспределение: заявка закреплена за менеджером vk={assigned_manager_vk_id}."
        else:
            notification_text += "\nАвтораспределение: свободный менеджер не найден, нужна ручная фиксация."
        await notify_assigned_manager(bot, notification_text, assigned_manager_vk_id)

        manager_hint = (
            "\nМенеджер уже занимается вашим вопросом."
            if assigned_manager_vk_id
            else "\nЗапрос передан команде менеджеров."
        )
        await message.answer(
            "Передал запрос менеджеру VIARE Travel.\n"
            "Ожидайте ответ в этом чате. Если хотите, пока можете продолжить подбор через «Подобрать тур»."
            + manager_hint,
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message()
    async def fallback_handler(message: Message) -> None:
        text = (message.text or "").strip()
        role = None if _is_forced_client_mode(message.peer_id) else await get_staff_role(message.from_id)
        if text.startswith("/"):
            command = text.split(maxsplit=1)[0].lower()

            # Defensive fallback for staff commands in case mobile client sends extra characters
            # and strict command matcher misses.
            if role in {"admin", "manager"} and command in {"/admin", "/staff"}:
                if command == "/admin" and role != "admin":
                    await message.answer(
                        "Команда /admin доступна только администратору.\n"
                        "Открываю панель менеджера.",
                        keyboard=get_staff_menu_keyboard("manager"),
                    )
                    return
                await message.answer(
                    "Открываю панель сотрудника.",
                    keyboard=get_staff_menu_keyboard(role),
                )
                return

            if role == "admin" and command in {"/admin_help", "/manager_howto"}:
                await message.answer(
                    "Админ-подсказка:\n"
                    "- Панель: /admin\n"
                    "- Менеджеры: /managers /manager_add /manager_remove\n"
                    "- Гайд: /manager_howto\n"
                    "- Роль: /role",
                    keyboard=get_staff_menu_keyboard("admin"),
                )
                return

            if role == "manager" and command == "/manager_help":
                await message.answer(
                    "Подсказка менеджера:\n"
                    "- Панель: /staff\n"
                    "- Заявки: /requests /request_next\n"
                    "- Ответ: /reply_request\n"
                    "- Роль: /role",
                    keyboard=get_staff_menu_keyboard("manager"),
                )
                return

            if role == "admin":
                await message.answer(
                    "Неизвестная команда.\n"
                    "Подсказка администратора: /admin_help\n"
                    "Чтобы открыть панель: /admin"
                )
                return
            if role == "manager":
                await message.answer(
                    "Неизвестная команда.\n"
                    "Подсказка менеджера: /manager_help\n"
                    "Чтобы открыть панель: /staff"
                )
                return
            await message.answer("Неизвестная команда.\nНапишите /menu для меню или /help для подсказки.")
            return

        logger.debug("Fallback triggered for message: %s", text)
        if message.peer_id >= 2_000_000_000:
            await message.answer(
                "Если вы пишете в общем чате, нажимайте кнопки меню или откройте личные сообщения сообщества.\n"
                "Для старта можно написать /menu.",
                keyboard=get_main_menu_keyboard(),
            )
            return

        if role:
            await message.answer(
                "Не понял запрос.\n"
                "Используйте кнопки панели или команды /manager_help /admin_help.\n"
                "Для возврата в панель: /staff или /admin."
            )
            return

        await message.answer(
            "Не понял запрос.\n"
            "Используйте кнопки меню или напишите /menu.\n"
            "Если нужен пример, нажмите «Как пользоваться».",
            keyboard=get_main_menu_keyboard(),
        )
