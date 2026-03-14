from __future__ import annotations

import random
from pathlib import Path

from vkbottle.bot import Bot, BotLabeler, Message

from keyboards.main_menu import get_main_menu_keyboard, get_staff_menu_keyboard
from services.admin import add_log, get_stats
from services.auth import get_staff_role, is_admin, is_staff
from services.content import get_content_block, update_content_block
from services.exports import export_requests_csv, export_requests_xlsx
from services.requests import (
    get_latest_request_by_vk_id,
    get_next_request,
    get_request_by_id,
    list_requests,
    update_request_status,
)
from services.tours import create_tour, get_tour_by_id, list_tours_admin, set_tour_active, update_tour_price
from services.users import list_users
from services.vk_media import upload_document
from utils.formatting import format_request_card, format_request_list_item
from utils.states import AdminState
from utils.validators import normalize_country, normalize_rest_type, parse_budget, parse_date_range

CANCEL_TEXTS = {"отмена", "cancel"}
MAIN_MENU_TEXTS = {"в меню", "меню", "/menu"}
PANEL_EXIT_TEXTS = {"выйти из панели", "/exit_panel"}
PANEL_OPEN_TEXTS = {"/admin", "/staff"}
USER_MENU_BUTTONS = {
    "подобрать тур",
    "все туры",
    "faq",
    "контакты",
    "оплата и бронирование",
    "услуги viare travel",
    "о viare travel",
    "связаться с менеджером",
}
REQUEST_FILTER_BUTTONS = {
    "Новые": "new",
    "В работе": "in_progress",
    "Ждут клиента": "waiting_client",
    "Закрытые": "closed",
}
CONTENT_LABELS = {
    "FAQ текст": "faq",
    "Контакты текст": "contacts",
    "Оплата текст": "payment",
}
STAFF_ACTION_TEXTS = {
    "заявки",
    "следующая заявка",
    "карточка заявки",
    "ответ по заявке",
    "ответ по vk id",
    "закрыть заявку",
    "статистика",
    "пользователи",
    "выгрузка заявок",
    "туры админ",
    "faq текст",
    "контакты текст",
    "оплата текст",
    "рассылка",
    "новые",
    "в работе",
    "ждут клиента",
    "закрытые",
    "/requests",
    "/request",
    "/request_next",
    "/request_card",
    "/request_close",
    "/reply",
    "/reply_request",
    "/stats",
    "/users",
    "/requests_export",
    "/tour_list",
    "/tour_add",
    "/tour_disable",
    "/tour_enable",
    "/tour_price",
    "/broadcast",
}


def _normalized_text(message: Message) -> str:
    return (message.text or "").strip().lower()


def _staff_keyboard(role: str | None) -> str:
    return get_staff_menu_keyboard(role or "manager")


async def _ensure_staff(message: Message) -> bool:
    if await is_staff(message.from_id):
        return True
    await message.answer("Эта команда доступна только менеджеру или администратору.", keyboard=get_main_menu_keyboard())
    return False


async def _ensure_admin(message: Message) -> bool:
    if await is_admin(message.from_id):
        return True
    await message.answer("Этот раздел доступен только администратору.", keyboard=get_main_menu_keyboard())
    return False


def _parse_reply_payload(text: str) -> tuple[int, str] | None:
    value = (text or "").strip()
    if not value:
        return None

    if "|" in value:
        left, right = value.split("|", 1)
        left = left.strip()
        right = right.strip()
        if left.isdigit() and right:
            return int(left), right
        return None

    parts = value.split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].strip():
        return None
    return int(parts[0]), parts[1].strip()


def _parse_tour_location(text: str) -> tuple[str | None, str | None, str | None]:
    raw = (text or "").strip()
    if not raw:
        return None, None, None

    country_text = raw
    destination = None
    if "|" in raw:
        country_text, destination_text = raw.split("|", 1)
        country_text = country_text.strip()
        destination = destination_text.strip() or None

    country = normalize_country(country_text)
    if not country:
        return None, None, None

    if country.lower() == "россия":
        if destination:
            destination = " ".join(word.capitalize() for word in destination.split())
        return "domestic", country, destination

    return "abroad", country, country


async def _send_text(bot: Bot, peer_id: int, text: str, attachment: str | None = None) -> None:
    await bot.api.messages.send(
        peer_id=peer_id,
        message=text,
        attachment=attachment,
        random_id=random.randint(1, 2_000_000_000),
    )


async def _send_manager_reply(bot: Bot, vk_id: int, text: str) -> None:
    await bot.api.messages.send(
        user_id=vk_id,
        message=f"Менеджер VIARE Travel:\n{text}",
        random_id=random.randint(1, 2_000_000_000),
    )


def _requests_hint_lines() -> list[str]:
    return [
        "Что можно сделать дальше:",
        "- Открыть карточку: /request_card",
        "- Ответить клиенту: /reply_request",
        "- Взять следующую заявку: /request_next",
    ]


async def _show_staff_panel(message: Message) -> None:
    role = await get_staff_role(message.from_id)
    title = "Панель администратора" if role == "admin" else "Панель менеджера"
    lines = [title, "", "Доступные действия: работа с заявками, ответы клиентам и быстрые фильтры."]
    if role == "admin":
        lines.append("Дополнительно доступны статистика, пользователи, выгрузка, управление турами и контентом.")
    lines.append("")
    lines.append("Нажмите кнопку ниже или используйте команду.")
    await message.answer("\n".join(lines), keyboard=_staff_keyboard(role))


async def _show_filtered_requests(message: Message, status: str | None = None) -> None:
    rows = await list_requests(limit=15, status=status)
    role = await get_staff_role(message.from_id)
    if not rows:
        await message.answer("Подходящих заявок пока нет.", keyboard=_staff_keyboard(role))
        return

    lines = ["Список заявок:", ""]
    lines.extend(format_request_list_item(row) for row in rows)
    lines.extend(["", *_requests_hint_lines()])
    await message.answer("\n".join(lines), keyboard=_staff_keyboard(role))


async def _handle_state_escape(bot: Bot, message: Message) -> bool:
    text = _normalized_text(message)
    role = await get_staff_role(message.from_id)

    if text in CANCEL_TEXTS:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Процесс выполнен. Текущий ввод отменен.", keyboard=_staff_keyboard(role))
        return True

    if text in PANEL_EXIT_TEXTS:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Процесс выполнен. Вы вышли из панели.", keyboard=get_main_menu_keyboard())
        return True

    if text in MAIN_MENU_TEXTS:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Процесс выполнен. Возвращаю в главное меню.", keyboard=get_main_menu_keyboard())
        return True

    if text in PANEL_OPEN_TEXTS:
        await bot.state_dispenser.delete(message.peer_id)
        await _show_staff_panel(message)
        return True

    if text in STAFF_ACTION_TEXTS or text in USER_MENU_BUTTONS:
        await bot.state_dispenser.delete(message.peer_id)
        keyboard = _staff_keyboard(role) if text in STAFF_ACTION_TEXTS else get_main_menu_keyboard()
        await message.answer(
            "Предыдущий ввод отменен. Нажмите нужную кнопку или повторите команду еще раз.",
            keyboard=keyboard,
        )
        return True

    return False


async def _set_state(bot: Bot, peer_id: int, state: str, payload: dict | None = None) -> None:
    await bot.state_dispenser.set(peer_id, state, **(payload or {}))


async def _show_tours_admin_list(message: Message) -> None:
    tours = await list_tours_admin(limit=25)
    role = await get_staff_role(message.from_id)
    if not tours:
        await message.answer("Туров пока нет.", keyboard=_staff_keyboard(role))
        return

    lines = ["Туры в системе:", ""]
    for tour in tours:
        status = "активен" if int(tour.get("is_active") or 0) == 1 else "выключен"
        destination = tour.get("destination") or tour.get("country") or "без направления"
        photo_mark = "есть фото" if tour.get("photo_url") else "без фото"
        lines.append(
            f"#{tour['id']} | {tour['name']} | {destination} | "
            f"{tour['price_per_person']} ₽/чел. | {status} | {photo_mark}"
        )

    lines.extend(
        [
            "",
            "Команды:",
            "/tour_add",
            "/tour_disable",
            "/tour_enable",
            "/tour_price",
        ]
    )
    await message.answer("\n".join(lines), keyboard=_staff_keyboard(role))


def register_admin_handlers(labeler: BotLabeler, bot: Bot) -> None:
    @labeler.message(text=["/admin", "/staff"])
    async def open_staff_panel(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_staff_panel(message)

    @labeler.message(text=["Выйти из панели", "/exit_panel"])
    async def exit_staff_panel(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Процесс выполнен. Вы вышли из панели.", keyboard=get_main_menu_keyboard())

    @labeler.message(text=["/requests", "/request", "Заявки"])
    async def requests_handler(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await _show_filtered_requests(message)

    @labeler.message(text=["Новые", "В работе", "Ждут клиента", "Закрытые"])
    async def requests_filtered_handler(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        status = REQUEST_FILTER_BUTTONS.get((message.text or "").strip())
        await _show_filtered_requests(message, status=status)

    @labeler.message(text=["/request_next", "Следующая заявка"])
    async def next_request_handler(message: Message) -> None:
        if not await _ensure_staff(message):
            return

        request = await get_next_request(("new", "in_progress", "waiting_client"))
        role = await get_staff_role(message.from_id)
        if not request:
            await message.answer("Активных заявок сейчас нет.", keyboard=_staff_keyboard(role))
            return

        if request.get("status") == "new":
            await update_request_status(int(request["id"]), "in_progress")
            request["status"] = "in_progress"

        await message.answer(format_request_card(request), keyboard=_staff_keyboard(role))

    @labeler.message(text=["/request_card", "Карточка заявки"])
    async def request_card_prompt(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await _set_state(bot, message.peer_id, AdminState.REQUEST_CARD)
        await message.answer(
            "Введите ID заявки.\nПример: 25\n\nДля выхода напишите «Отмена».",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.REQUEST_CARD)
    async def request_card_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен ID заявки. Пример: 25")
            return

        request = await get_request_by_id(int(text))
        if not request:
            await message.answer("Заявка с таким ID не найдена. Попробуйте еще раз.")
            return

        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(format_request_card(request), keyboard=_staff_keyboard(await get_staff_role(message.from_id)))

    @labeler.message(text=["/request_close", "Закрыть заявку"])
    async def request_close_prompt(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await _set_state(bot, message.peer_id, AdminState.REQUEST_CLOSE)
        await message.answer(
            "Введите ID заявки, которую нужно закрыть.\nПример: 25",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.REQUEST_CLOSE)
    async def request_close_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен ID заявки. Пример: 25")
            return

        request_id = int(text)
        request = await get_request_by_id(request_id)
        if not request:
            await message.answer("Заявка с таким ID не найдена.")
            return

        await update_request_status(request_id, "closed")
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Процесс выполнен. Заявка #{request_id} закрыта.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["/reply", "Ответ по VK ID"])
    async def reply_vk_prompt(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await _set_state(bot, message.peer_id, AdminState.REPLY_VK)
        await message.answer(
            "Введите VK ID и текст ответа.\nПример: 577900016 | Здравствуйте! Нашел подходящие варианты на ваши даты.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.REPLY_VK)
    async def reply_vk_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        parsed = _parse_reply_payload(message.text or "")
        if not parsed:
            await message.answer(
                "Нужен формат: VK ID | текст ответа\nПример: 577900016 | Здравствуйте! Нашел подходящие варианты."
            )
            return

        vk_id, reply_text = parsed
        await bot.state_dispenser.delete(message.peer_id)
        await _send_manager_reply(bot, vk_id, reply_text)

        latest_request = await get_latest_request_by_vk_id(vk_id)
        if latest_request and latest_request.get("status") != "closed":
            await update_request_status(int(latest_request["id"]), "waiting_client")

        await add_log(None, "manager_reply_vk", f"Reply sent to vk_id={vk_id}")
        await message.answer(
            "Ответ отправлен клиенту. Последняя заявка переведена в статус «Ждет клиента».",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["/reply_request", "Ответ по заявке"])
    async def reply_request_prompt(message: Message) -> None:
        if not await _ensure_staff(message):
            return
        await _set_state(bot, message.peer_id, AdminState.REPLY_REQUEST)
        await message.answer(
            "Введите ID заявки и текст ответа.\nПример: 25 | Здравствуйте! Нашел подходящие варианты на ваши даты.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.REPLY_REQUEST)
    async def reply_request_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        parsed = _parse_reply_payload(message.text or "")
        if not parsed:
            await message.answer(
                "Нужен формат: ID заявки | текст ответа\nПример: 25 | Здравствуйте! Нашел подходящие варианты."
            )
            return

        request_id, reply_text = parsed
        request = await get_request_by_id(request_id)
        if not request:
            await message.answer("Заявка с таким ID не найдена.")
            return

        await bot.state_dispenser.delete(message.peer_id)
        await _send_manager_reply(bot, int(request["vk_id"]), reply_text)
        await update_request_status(request_id, "waiting_client")
        await add_log(None, "manager_reply_request", f"Reply sent for request_id={request_id}")
        await message.answer(
            f"Ответ по заявке #{request_id} отправлен. Статус обновлен на «Ждет клиента».",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["/stats", "Статистика"])
    async def stats_handler(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        stats = await get_stats()
        await message.answer(
            "Статистика проекта:\n"
            f"- Пользователи: {stats['users']}\n"
            f"- Заявки: {stats['requests']}\n"
            f"- Активные туры: {stats['tours']}\n"
            f"- Логи: {stats['logs']}",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["/users", "Пользователи"])
    async def users_handler(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        rows = await list_users(limit=20)
        if not rows:
            await message.answer("Пользователей пока нет.", keyboard=_staff_keyboard(await get_staff_role(message.from_id)))
            return

        lines = ["Последние пользователи:", ""]
        for row in rows:
            role_parts: list[str] = []
            if int(row.get("is_admin") or 0) == 1:
                role_parts.append("админ")
            if int(row.get("is_manager") or 0) == 1 and "админ" not in role_parts:
                role_parts.append("менеджер")
            role_text = ", ".join(role_parts) if role_parts else "клиент"
            lines.append(f"#{row['id']} | vk={row['vk_id']} | {role_text} | {row['created_at']}")

        await message.answer("\n".join(lines), keyboard=_staff_keyboard(await get_staff_role(message.from_id)))

    @labeler.message(text=["/requests_export", "Выгрузка заявок"])
    async def export_requests_handler(message: Message) -> None:
        if not await _ensure_admin(message):
            return

        csv_path = await export_requests_csv()
        attachments: list[str] = []
        csv_attachment = await upload_document(Path(csv_path), csv_path.name)
        if csv_attachment:
            attachments.append(csv_attachment)

        xlsx_path = await export_requests_xlsx()
        if xlsx_path:
            xlsx_attachment = await upload_document(Path(xlsx_path), xlsx_path.name)
            if xlsx_attachment:
                attachments.append(xlsx_attachment)

        await _send_text(
            bot,
            message.peer_id,
            "Процесс выполнен. Файлы выгрузки подготовлены.",
            attachment=",".join(attachments) if attachments else None,
        )

    @labeler.message(text=["/tour_list", "Туры админ"])
    async def tour_list_handler(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _show_tours_admin_list(message)

    @labeler.message(text="/tour_add")
    async def tour_add_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_NAME)
        await message.answer(
            "Введите название тура.\nПример: Сочи Weekend",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.TOUR_ADD_NAME)
    async def tour_add_name_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return
        name = (message.text or "").strip()
        if len(name) < 3:
            await message.answer("Название слишком короткое. Попробуйте еще раз.")
            return
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_COUNTRY, {"name": name})
        await message.answer(
            "Введите страну.\nДля России можно так: Россия | Сочи\nДля зарубежья: Турция",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.TOUR_ADD_COUNTRY)
    async def tour_add_country_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        travel_scope, country, destination = _parse_tour_location(message.text or "")
        if not country or not travel_scope:
            await message.answer("Не понял направление. Пример: Россия | Сочи или Турция")
            return

        payload = dict(message.state_peer.payload or {})
        payload.update(
            {
                "travel_scope": travel_scope,
                "country": country,
                "destination": destination,
            }
        )
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_PRICE, payload)
        await message.answer("Введите цену за человека в рублях.\nПример: 95000")

    @labeler.message(state=AdminState.TOUR_ADD_PRICE)
    async def tour_add_price_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return
        price = parse_budget(message.text or "")
        if not price:
            await message.answer("Некорректная цена. Пример: 95000")
            return

        payload = dict(message.state_peer.payload or {})
        payload["price_per_person"] = price
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_DAYS, payload)
        await message.answer("Введите длительность тура в днях.\nПример: 7")

    @labeler.message(state=AdminState.TOUR_ADD_DAYS)
    async def tour_add_days_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return
        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужно число дней. Пример: 7")
            return

        days = int(text)
        if days < 2 or days > 30:
            await message.answer("Длительность должна быть от 2 до 30 дней.")
            return

        payload = dict(message.state_peer.payload or {})
        payload["duration_days"] = days
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_REST, payload)
        await message.answer(
            "Введите тип отдыха.\nДоступно: пляжный, экскурсионный, активный, семейный, горнолыжный, оздоровительный"
        )

    @labeler.message(state=AdminState.TOUR_ADD_REST)
    async def tour_add_rest_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        rest_type = normalize_rest_type(message.text or "")
        if not rest_type or rest_type == "any":
            await message.answer("Нужен конкретный тип отдыха. Пример: семейный")
            return

        payload = dict(message.state_peer.payload or {})
        payload["rest_type"] = rest_type
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_DATES, payload)
        await message.answer("Введите диапазон доступности.\nПример: 01.06.2026 - 30.09.2026")

    @labeler.message(state=AdminState.TOUR_ADD_DATES)
    async def tour_add_dates_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        dates = parse_date_range(message.text or "")
        if not dates:
            await message.answer("Не понял даты. Пример: 01.06.2026 - 30.09.2026")
            return

        start_date, end_date = dates
        payload = dict(message.state_peer.payload or {})
        payload["available_from"] = start_date
        payload["available_to"] = end_date
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_DESCRIPTION, payload)
        await message.answer("Введите краткое описание тура.")

    @labeler.message(state=AdminState.TOUR_ADD_DESCRIPTION)
    async def tour_add_description_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        description = (message.text or "").strip()
        if len(description) < 10:
            await message.answer("Описание слишком короткое. Сделайте его чуть подробнее.")
            return

        payload = dict(message.state_peer.payload or {})
        payload["description"] = description
        await _set_state(bot, message.peer_id, AdminState.TOUR_ADD_PHOTO, payload)
        await message.answer("Пришлите ссылку на фото тура или напишите «-», если фото пока нет.")

    @labeler.message(state=AdminState.TOUR_ADD_PHOTO)
    async def tour_add_photo_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        photo_text = (message.text or "").strip()
        photo_url = None if photo_text in {"-", "нет", "без фото"} else photo_text
        if photo_url and not photo_url.lower().startswith(("http://", "https://")):
            await message.answer("Нужна ссылка вида https://... или символ «-».")
            return

        payload = dict(message.state_peer.payload or {})
        await create_tour(
            name=str(payload["name"]),
            country=str(payload["country"]),
            destination=payload.get("destination"),
            travel_scope=payload.get("travel_scope"),
            price_per_person=int(payload["price_per_person"]),
            duration_days=int(payload["duration_days"]),
            rest_type=str(payload["rest_type"]),
            available_from=str(payload["available_from"]),
            available_to=str(payload["available_to"]),
            description=str(payload["description"]),
            photo_url=photo_url,
        )
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "Процесс выполнен. Тур добавлен в каталог.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text="/tour_disable")
    async def tour_disable_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _set_state(bot, message.peer_id, AdminState.TOUR_DISABLE)
        await message.answer("Введите ID тура, который нужно выключить.")

    @labeler.message(state=AdminState.TOUR_DISABLE)
    async def tour_disable_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен ID тура.")
            return

        tour = await get_tour_by_id(int(text))
        if not tour:
            await message.answer("Тур с таким ID не найден.")
            return

        await set_tour_active(int(text), False)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Процесс выполнен. Тур #{text} отключен.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text="/tour_enable")
    async def tour_enable_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _set_state(bot, message.peer_id, AdminState.TOUR_ENABLE)
        await message.answer("Введите ID тура, который нужно снова включить.")

    @labeler.message(state=AdminState.TOUR_ENABLE)
    async def tour_enable_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Нужен ID тура.")
            return

        tour = await get_tour_by_id(int(text))
        if not tour:
            await message.answer("Тур с таким ID не найден.")
            return

        await set_tour_active(int(text), True)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Процесс выполнен. Тур #{text} снова активен.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text="/tour_price")
    async def tour_price_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _set_state(bot, message.peer_id, AdminState.TOUR_PRICE)
        await message.answer("Введите ID тура и новую цену.\nПример: 12 | 125000")

    @labeler.message(state=AdminState.TOUR_PRICE)
    async def tour_price_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        parsed = _parse_reply_payload(message.text or "")
        if not parsed:
            await message.answer("Нужен формат: ID тура | цена\nПример: 12 | 125000")
            return

        tour_id, price_value = parsed
        price = parse_budget(price_value)
        if not price:
            await message.answer("Некорректная цена. Пример: 125000")
            return

        tour = await get_tour_by_id(tour_id)
        if not tour:
            await message.answer("Тур с таким ID не найден.")
            return

        await update_tour_price(tour_id, price)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            f"Процесс выполнен. Цена тура #{tour_id} обновлена до {price} ₽.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["FAQ текст", "Контакты текст", "Оплата текст"])
    async def content_edit_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        content_key = CONTENT_LABELS.get((message.text or "").strip())
        if not content_key:
            return

        current_text = await get_content_block(content_key)
        await _set_state(bot, message.peer_id, AdminState.CONTENT_EDIT, {"content_key": content_key})
        await message.answer(
            f"Текущий текст блока «{message.text}»:\n\n{current_text}\n\nПришлите новый текст целиком.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.CONTENT_EDIT)
    async def content_edit_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        new_value = (message.text or "").strip()
        if len(new_value) < 10:
            await message.answer("Текст слишком короткий. Пришлите полный блок.")
            return

        payload = dict(message.state_peer.payload or {})
        content_key = payload.get("content_key")
        if not content_key:
            await bot.state_dispenser.delete(message.peer_id)
            await message.answer("Не удалось определить редактируемый блок. Откройте панель заново.")
            return

        await update_content_block(str(content_key), new_value)
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "Процесс выполнен. Текст обновлен.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(text=["/broadcast", "Рассылка"])
    async def broadcast_prompt(message: Message) -> None:
        if not await _ensure_admin(message):
            return
        await _set_state(bot, message.peer_id, AdminState.BROADCAST)
        await message.answer(
            "Введите текст рассылки. Он будет отправлен всем пользователям бота.",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )

    @labeler.message(state=AdminState.BROADCAST)
    async def broadcast_state(message: Message) -> None:
        if await _handle_state_escape(bot, message):
            return

        text = (message.text or "").strip()
        if len(text) < 3:
            await message.answer("Текст слишком короткий. Пришлите нормальное сообщение для рассылки.")
            return

        recipients = await list_users(limit=10000)
        success = 0
        failed = 0
        for user in recipients:
            try:
                await bot.api.messages.send(
                    user_id=int(user["vk_id"]),
                    message=text,
                    random_id=random.randint(1, 2_000_000_000),
                )
                success += 1
            except Exception:
                failed += 1

        await bot.state_dispenser.delete(message.peer_id)
        await add_log(None, "broadcast", f"Broadcast sent success={success}, failed={failed}")
        await message.answer(
            f"Процесс выполнен. Рассылка завершена.\nУспешно: {success}\nС ошибкой: {failed}",
            keyboard=_staff_keyboard(await get_staff_role(message.from_id)),
        )
