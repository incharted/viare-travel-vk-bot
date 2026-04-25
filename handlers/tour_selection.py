from __future__ import annotations

import logging
from datetime import date

from vkbottle.bot import Bot, BotLabeler, Message

from keyboards.main_menu import (
    get_back_to_menu_keyboard,
    get_country_keyboard,
    get_destination_scope_keyboard,
    get_domestic_destination_keyboard,
    get_main_menu_keyboard,
    get_month_keyboard,
    get_request_confirmation_keyboard,
    get_rest_type_keyboard,
)
from services.admin import add_log
from services.assignment import auto_assign_request
from services.notifications import notify_assigned_manager
from services.requests import create_request
from services.tour_operator_api import fetch_external_offers
from services.tours import (
    find_cheapest_destination_tours,
    find_smart_date_suggestions,
    find_tours,
    find_tours_flexible,
    get_destination_availability,
    list_available_countries,
    list_domestic_destinations,
)
from services.users import get_user_by_vk_id, upsert_user
from services.vk_media import send_tour_message
from utils.formatting import format_request_notification, format_request_summary_for_confirmation
from utils.states import TourSelectionState
from utils.validators import (
    normalize_country,
    normalize_rest_type,
    parse_budget,
    parse_date_range,
    parse_exact_date_range,
    parse_travelers,
)

logger = logging.getLogger(__name__)

ABROAD_COUNTRY_DESCRIPTIONS = {
    "Абхазия": "Море, горы и простой курортный отдых без сложной логистики.",
    "Армения": "Ереван, гастрономия, горные виды и короткие экскурсионные поездки.",
    "Беларусь": "Санатории, спокойный отдых и короткие городские поездки.",
    "Вьетнам": "Пляжи, мягкий климат и доступный азиатский отдых.",
    "Грузия": "Вкусная кухня, Тбилиси, горы и атмосферные маршруты.",
    "Египет": "Красное море, пляжи, дайвинг и формат all inclusive.",
    "Китай": "Хайнань, мегаполисы и насыщенные экскурсионные маршруты.",
    "Мальдивы": "Премиальный островной отдых, уединение и красивые лагуны.",
    "ОАЭ": "Дубай, высокий сервис, пляжи, шопинг и городской комфорт.",
    "Таиланд": "Теплое море, тропики, пляжный отдых и активная ночная жизнь.",
    "Турция": "Комфортный пляжный отдых, family-формат и удобные пакеты.",
    "Узбекистан": "Самарканд, Бухара, восточная архитектура и экскурсии.",
    "Шри-Ланка": "Океан, тропическая природа и спокойный отдых у воды.",
}

DOMESTIC_DESTINATION_DESCRIPTIONS = {
    "Адлер": "Пляжи, набережная и удобный короткий перелет.",
    "Алтай": "Горы, реки и активный отдых на природе.",
    "Байкал": "Озеро, трекинг и красивые природные маршруты.",
    "Владивосток": "Морской город, бухты и дальневосточная атмосфера.",
    "Домбай": "Горные виды, прогулки и свежий воздух.",
    "Кавказские Минеральные Воды": "Санатории, восстановление и спокойный ритм отдыха.",
    "Казань": "Городской уикенд, гастрономия и исторический центр.",
    "Калининград": "Европейская атмосфера, Балтика и экскурсии.",
    "Карелия": "Озера, леса и расслабленный отдых на природе.",
    "Красная Поляна": "Горы, канатные дороги и активный формат отдыха.",
    "Санкт-Петербург": "Музеи, каналы и насыщенная культурная поездка.",
    "Сочи": "Море, сервис и удобный семейный отдых.",
    "Шерегеш": "Снег, трассы и горнолыжный формат зимой.",
}

WIZARD_TOTAL_STEPS = 6


def _normalize_choice(text: str, options: list[str]) -> str | None:
    lowered = text.strip().lower()
    for option in options:
        if option.lower() == lowered:
            return option
    return None


def _format_destinations_prompt(title: str, items: list[str], descriptions: dict[str, str]) -> str:
    lines = [title]
    for item in items:
        lines.append(f"- {item}: {descriptions.get(item, 'Подберем варианты под ваш запрос.')}")
    return "\n".join(lines)


def _format_availability_hint(availability: dict | None, travelers: int) -> str:
    if not availability:
        return ""

    rest_types = ", ".join(availability.get("rest_types", [])[:4]) or "разные форматы"
    min_budget = availability.get("min_total_price")
    min_budget_text = f"от {min_budget:,} ₽".replace(",", " ") if min_budget else "по запросу"
    return (
        "Подсказка по направлению:\n"
        f"- доступно туров: {availability.get('tours_count', 0)}\n"
        f"- примерный сезон: {availability.get('min_available_from')} - {availability.get('max_available_to')}\n"
        f"- форматы: {rest_types}\n"
        f"- ориентир по бюджету на {travelers} чел.: {min_budget_text}"
    )


def _format_human_date(iso_date: str | None) -> str:
    if not iso_date:
        return "-"
    try:
        return date.fromisoformat(iso_date).strftime("%d.%m.%Y")
    except ValueError:
        return iso_date


def _format_smart_dates_hint(suggestions: list[dict]) -> str:
    if not suggestions:
        return ""

    lines = [
        "Умные даты: нашёл более удобные окна сдвига по этому направлению.",
        "Можно немного сдвинуть даты и получить подходящие варианты:",
    ]
    for item in suggestions:
        shift = int(item.get("shift_days") or 0)
        shift_text = f"+{shift} дн." if shift > 0 else f"{shift} дн."
        total_price = int(item.get("total_price") or 0)
        total_text = f"{total_price:,}".replace(",", " ")
        saving = item.get("savings_vs_exact")
        if isinstance(saving, int) and saving > 0:
            saving_text = f" (экономия около {saving:,} ₽)".replace(",", " ")
        else:
            saving_text = ""
        lines.append(
            f"- {_format_human_date(str(item.get('start_date')))} - {_format_human_date(str(item.get('end_date')))} "
            f"({shift_text}), ориентир {total_text} ₽{saving_text}"
        )

    lines.append("Если подходит один из вариантов, подтвердите заявку, и менеджер быстро всё оформит.")
    return "\n".join(lines)


def _step_header(step: int, title: str) -> str:
    return f"Шаг {step}/{WIZARD_TOTAL_STEPS}. {title}"


async def _ensure_user(message: Message) -> int:
    user = await get_user_by_vk_id(message.from_id)
    if user:
        return int(user["id"])
    return await upsert_user(message.from_id)


async def _show_scope_step(bot: Bot, message: Message) -> None:
    await bot.state_dispenser.set(message.peer_id, TourSelectionState.SCOPE)
    await message.answer(
        _step_header(1, "Выберите формат поездки: по России или за границу.")
        + "\nПодсказка: используйте кнопки ниже.",
        keyboard=get_destination_scope_keyboard(),
    )


async def _load_preview_tours(payload: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    exact_local_tours = await find_tours(
        travel_scope=payload["travel_scope"],
        country=payload["country"],
        destination=payload.get("destination"),
        budget=int(payload["budget"]),
        travelers=int(payload["travelers"]),
        start_date=str(payload["start_date"]),
        end_date=str(payload["end_date"]),
        rest_type=str(payload["rest_type"]),
        limit=5,
    )

    flexible_local_tours: list[dict] = []
    cheapest_local_tours: list[dict] = []
    external_tours: list[dict] = []

    if not exact_local_tours:
        flexible_local_tours = await find_tours_flexible(
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload.get("destination"),
            budget=int(payload["budget"]),
            travelers=int(payload["travelers"]),
            start_date=str(payload["start_date"]),
            end_date=str(payload["end_date"]),
            rest_type=str(payload["rest_type"]),
            limit=5,
        )

    if not exact_local_tours and not flexible_local_tours:
        cheapest_local_tours = await find_cheapest_destination_tours(
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload.get("destination"),
            travelers=int(payload["travelers"]),
            limit=5,
        )

    if (
        not exact_local_tours
        and not flexible_local_tours
        and not cheapest_local_tours
        and payload["travel_scope"] == "abroad"
    ):
        external_tours = await fetch_external_offers(
            country=str(payload["country"]),
            budget=int(payload["budget"]),
            travelers=int(payload["travelers"]),
            start_date=str(payload["start_date"]),
            end_date=str(payload["end_date"]),
            rest_type=str(payload["rest_type"]),
        )

    return exact_local_tours, flexible_local_tours, cheapest_local_tours, external_tours


def register_tour_handlers(labeler: BotLabeler, bot: Bot) -> None:
    @labeler.message(text=["В меню", "Вернуться в меню"])
    async def return_to_menu(message: Message) -> None:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "Вернул вас в главное меню.",
            keyboard=get_main_menu_keyboard(),
        )

    @labeler.message(text=["Подобрать тур", "/tour", "Изменить запрос"])
    async def start_tour_flow(message: Message) -> None:
        await _show_scope_step(bot, message)

    @labeler.message(state=TourSelectionState.SCOPE)
    async def collect_scope(message: Message) -> None:
        text = (message.text or "").strip().lower()
        if text == "по россии":
            destinations = await list_domestic_destinations()
            await bot.state_dispenser.set(
                message.peer_id,
                TourSelectionState.DESTINATION,
                travel_scope="domestic",
                country="Россия",
            )
            await message.answer(
                _format_destinations_prompt(
                    _step_header(2, "Выберите направление по России из списка или напишите вручную.")
                    + "\nКоротко о направлениях:",
                    destinations,
                    DOMESTIC_DESTINATION_DESCRIPTIONS,
                ),
                keyboard=get_domestic_destination_keyboard(destinations) if destinations else get_back_to_menu_keyboard(),
            )
            return

        if text == "за границу":
            countries = await list_available_countries()
            await bot.state_dispenser.set(
                message.peer_id,
                TourSelectionState.DESTINATION,
                travel_scope="abroad",
            )
            await message.answer(
                _format_destinations_prompt(
                    _step_header(2, "Выберите страну из списка или напишите вручную.")
                    + "\nКоротко о странах:",
                    countries,
                    ABROAD_COUNTRY_DESCRIPTIONS,
                ),
                keyboard=get_country_keyboard(countries) if countries else get_back_to_menu_keyboard(),
            )
            return

        await message.answer(
            "Не понял формат поездки.\n"
            "Выберите один из вариантов кнопкой: «По России» или «За границу».",
            keyboard=get_destination_scope_keyboard(),
        )

    @labeler.message(state=TourSelectionState.DESTINATION)
    async def collect_destination(message: Message) -> None:
        payload = message.state_peer.payload
        scope = payload["travel_scope"]

        if scope == "domestic":
            destinations = await list_domestic_destinations()
            destination = _normalize_choice(message.text or "", destinations)
            if not destination:
                await message.answer(
                    "Не понял направление.\n"
                    "Выберите вариант кнопкой или напишите название ровно как в списке.\n"
                    "Пример: Сочи",
                    keyboard=get_domestic_destination_keyboard(destinations) if destinations else get_back_to_menu_keyboard(),
                )
                return
            country = "Россия"
        else:
            countries = await list_available_countries()
            country = normalize_country(message.text or "")
            if not country or country not in countries:
                await message.answer(
                    "Не понял страну.\n"
                    "Выберите вариант кнопкой или напишите название ровно как в списке.\n"
                    "Пример: Турция",
                    keyboard=get_country_keyboard(countries) if countries else get_back_to_menu_keyboard(),
                )
                return
            destination = country

        await bot.state_dispenser.set(
            message.peer_id,
            TourSelectionState.DATES,
            travel_scope=scope,
            country=country,
            destination=destination,
            awaiting_exact_dates=False,
        )
        await message.answer(
            _step_header(3, "Укажите даты поездки.")
            + "\nВыберите месяц кнопкой или нажмите «Точные даты».",
            keyboard=get_month_keyboard(),
        )

    @labeler.message(state=TourSelectionState.DATES)
    async def collect_dates(message: Message) -> None:
        text = (message.text or "").strip()
        payload = message.state_peer.payload

        if text.lower() == "точные даты":
            await bot.state_dispenser.set(
                message.peer_id,
                TourSelectionState.DATES,
                **payload,
                awaiting_exact_dates=True,
            )
            await message.answer(
                _step_header(3, "Введите точные даты.")
                + "\nФормат: ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
                "Пример: 10.07.2026 - 17.07.2026",
                keyboard=get_back_to_menu_keyboard(),
            )
            return

        date_range = parse_exact_date_range(text) if payload.get("awaiting_exact_dates") else parse_date_range(text)
        if not date_range:
            await message.answer(
                "Не понял даты.\n"
                "Выберите месяц кнопкой или введите диапазон в формате:\n"
                "10.06.2026 - 20.06.2026",
                keyboard=get_month_keyboard() if not payload.get("awaiting_exact_dates") else get_back_to_menu_keyboard(),
            )
            return

        start_date, end_date = date_range
        await bot.state_dispenser.set(
            message.peer_id,
            TourSelectionState.TRAVELERS,
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload["destination"],
            start_date=start_date,
            end_date=end_date,
        )
        await message.answer(
            _step_header(4, "Сколько туристов поедет?")
            + "\nВведите число от 1 до 15.\n"
            "Пример: 2",
            keyboard=get_back_to_menu_keyboard(),
        )

    @labeler.message(state=TourSelectionState.TRAVELERS)
    async def collect_travelers(message: Message) -> None:
        travelers = parse_travelers(message.text or "")
        if travelers is None:
            await message.answer(
                "Количество туристов должно быть числом от 1 до 15.\n"
                "Пример: 1, 2, 3",
                keyboard=get_back_to_menu_keyboard(),
            )
            return

        payload = message.state_peer.payload
        availability = await get_destination_availability(
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload.get("destination"),
            travelers=travelers,
        )
        await bot.state_dispenser.set(
            message.peer_id,
            TourSelectionState.BUDGET,
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload["destination"],
            start_date=payload["start_date"],
            end_date=payload["end_date"],
            travelers=travelers,
        )
        prompt = (
            _step_header(5, "Укажите максимальный бюджет в рублях.")
            + "\nПример: 180000"
        )
        hint = _format_availability_hint(availability, travelers)
        if hint:
            prompt = f"{prompt}\n\n{hint}"
        await message.answer(prompt, keyboard=get_back_to_menu_keyboard())

    @labeler.message(state=TourSelectionState.BUDGET)
    async def collect_budget(message: Message) -> None:
        budget = parse_budget(message.text or "")
        if budget is None:
            await message.answer(
                "Некорректный бюджет.\n"
                "Введите число от 10 000 до 20 000 000 без валюты.\n"
                "Пример: 200000",
                keyboard=get_back_to_menu_keyboard(),
            )
            return

        payload = message.state_peer.payload
        await bot.state_dispenser.set(
            message.peer_id,
            TourSelectionState.REST_TYPE,
            travel_scope=payload["travel_scope"],
            country=payload["country"],
            destination=payload["destination"],
            budget=budget,
            start_date=payload["start_date"],
            end_date=payload["end_date"],
            travelers=payload["travelers"],
        )
        await message.answer(
            _step_header(6, "Выберите тип отдыха.")
            + "\nЕсли формат не важен, нажмите «Любой тип отдыха».",
            keyboard=get_rest_type_keyboard(),
        )

    @labeler.message(state=TourSelectionState.REST_TYPE)
    async def collect_rest_type(message: Message) -> None:
        rest_type = normalize_rest_type(message.text or "")
        if not rest_type:
            await message.answer(
                "Неизвестный тип отдыха.\n"
                "Используйте кнопки: пляжный, экскурсионный, активный, семейный и т.д.",
                keyboard=get_rest_type_keyboard(),
            )
            return

        payload = message.state_peer.payload
        confirmation_payload = {
            "travel_scope": payload["travel_scope"],
            "country": payload["country"],
            "destination": payload["destination"],
            "budget": payload["budget"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "travelers": payload["travelers"],
            "rest_type": rest_type,
        }
        await bot.state_dispenser.set(message.peer_id, TourSelectionState.CONFIRMATION, **confirmation_payload)

        exact_local_tours, flexible_local_tours, cheapest_local_tours, external_tours = await _load_preview_tours(
            confirmation_payload
        )
        smart_date_suggestions: list[dict] = []
        if not exact_local_tours and not flexible_local_tours:
            smart_date_suggestions = await find_smart_date_suggestions(
                travel_scope=confirmation_payload["travel_scope"],
                country=confirmation_payload["country"],
                destination=confirmation_payload["destination"],
                travelers=int(confirmation_payload["travelers"]),
                rest_type=str(confirmation_payload["rest_type"]),
                start_date=str(confirmation_payload["start_date"]),
                end_date=str(confirmation_payload["end_date"]),
                limit=3,
            )
        await message.answer(
            "Проверка перед отправкой заявки:\n"
            + format_request_summary_for_confirmation(confirmation_payload),
            keyboard=get_request_confirmation_keyboard(),
        )

        if exact_local_tours:
            await message.answer(
                f"Нашел {len(exact_local_tours)} подходящих варианта по вашему запросу. Показываю лучшие:",
                keyboard=get_request_confirmation_keyboard(),
            )
            for tour in exact_local_tours[:3]:
                await send_tour_message(bot, message, tour, int(confirmation_payload["travelers"]))
            return

        if flexible_local_tours:
            await message.answer(
                "Точного совпадения не нашел, но есть близкие варианты в ваш бюджет. Показываю лучшее, что есть по направлению:",
                keyboard=get_request_confirmation_keyboard(),
            )
            for tour in flexible_local_tours[:3]:
                await send_tour_message(bot, message, tour, int(confirmation_payload["travelers"]))
            return

        if cheapest_local_tours:
            min_total = int(cheapest_local_tours[0]["price_per_person"]) * int(confirmation_payload["travelers"])
            min_total_text = f"{min_total:,}".replace(",", " ")
            await message.answer(
                "Под ваши даты и бюджет точного совпадения нет, но по этому направлению есть варианты чуть дороже.\n"
                f"Минимальный ориентир на ваш состав: от {min_total_text} ₽. Показываю ближайшие варианты:",
                keyboard=get_request_confirmation_keyboard(),
            )
            for tour in cheapest_local_tours[:3]:
                await send_tour_message(bot, message, tour, int(confirmation_payload["travelers"]))
            if smart_date_suggestions:
                await message.answer(
                    _format_smart_dates_hint(smart_date_suggestions),
                    keyboard=get_request_confirmation_keyboard(),
                )
            return

        if external_tours:
            await message.answer(
                f"В локальной базе нет точного совпадения, но нашел {len(external_tours)} актуальных варианта у партнера. Показываю лучшие:",
                keyboard=get_request_confirmation_keyboard(),
            )
            for tour in external_tours[:3]:
                await send_tour_message(bot, message, tour, int(confirmation_payload["travelers"]))
            if smart_date_suggestions:
                await message.answer(
                    _format_smart_dates_hint(smart_date_suggestions),
                    keyboard=get_request_confirmation_keyboard(),
                )
            return

        if smart_date_suggestions:
            await message.answer(
                _format_smart_dates_hint(smart_date_suggestions),
                keyboard=get_request_confirmation_keyboard(),
            )

        await message.answer(
            "Готовых совпадений прямо сейчас не нашел.\n"
            "Если нажмете «Подтверждаю», передам заявку менеджеру для ручного подбора.",
            keyboard=get_request_confirmation_keyboard(),
        )

    @labeler.message(state=TourSelectionState.CONFIRMATION)
    async def confirm_request(message: Message) -> None:
        text = (message.text or "").strip().lower()
        if text == "подтверждаю":
            payload = message.state_peer.payload
            await bot.state_dispenser.delete(message.peer_id)

            user_id = await _ensure_user(message)
            exact_local_tours, flexible_local_tours, cheapest_local_tours, external_tours = await _load_preview_tours(
                payload
            )
            manager_required = not bool(exact_local_tours or flexible_local_tours or external_tours)
            request_id = await create_request(
                user_id=user_id,
                travel_scope=payload["travel_scope"],
                country=payload["country"],
                destination=payload["destination"],
                budget=int(payload["budget"]),
                travelers=int(payload["travelers"]),
                start_date=str(payload["start_date"]),
                end_date=str(payload["end_date"]),
                rest_type=str(payload["rest_type"]),
                manager_required=manager_required,
            )

            if exact_local_tours:
                await add_log(user_id, "tours_found", f"request_id={request_id}; count={len(exact_local_tours)}")
            elif flexible_local_tours:
                await add_log(
                    user_id,
                    "tours_flexible_found",
                    f"request_id={request_id}; count={len(flexible_local_tours)}",
                )
            elif cheapest_local_tours:
                await add_log(
                    user_id,
                    "tours_over_budget_found",
                    f"request_id={request_id}; count={len(cheapest_local_tours)}",
                )
            elif external_tours:
                await add_log(user_id, "external_tours_found", f"request_id={request_id}; count={len(external_tours)}")
            else:
                await add_log(user_id, "no_tours_found", f"request_id={request_id}")

            notification_text = format_request_notification(
                request_id=request_id,
                user_vk_id=message.from_id,
                travel_scope=payload["travel_scope"],
                country=payload["country"],
                destination=payload["destination"],
                budget=int(payload["budget"]),
                travelers=int(payload["travelers"]),
                start_date=str(payload["start_date"]),
                end_date=str(payload["end_date"]),
                rest_type=str(payload["rest_type"]),
                manager_required=manager_required,
            )
            if exact_local_tours:
                notification_text += f"\nАвтоподбор: найдены точные локальные варианты ({len(exact_local_tours)} шт.)."
            elif flexible_local_tours:
                notification_text += f"\nАвтоподбор: найдены близкие локальные варианты ({len(flexible_local_tours)} шт.)."
            elif cheapest_local_tours:
                notification_text += f"\nАвтоподбор: есть варианты выше бюджета ({len(cheapest_local_tours)} шт.)."
            elif external_tours:
                notification_text += f"\nАвтоподбор: найдены внешние варианты ({len(external_tours)} шт.)."
            else:
                notification_text += "\nАвтоподбор: нужен ручной подбор менеджером."
            assigned_manager_vk_id = await auto_assign_request(request_id)
            if assigned_manager_vk_id:
                notification_text += f"\nАвтораспределение: заявка закреплена за менеджером vk={assigned_manager_vk_id}."
            else:
                notification_text += "\nАвтораспределение: свободный менеджер не найден, нужна ручная фиксация."
            await notify_assigned_manager(bot, notification_text, assigned_manager_vk_id)

            if exact_local_tours or flexible_local_tours or cheapest_local_tours or external_tours:
                manager_hint = (
                    "\nМенеджер уже занимается вашим вопросом."
                    if assigned_manager_vk_id
                    else "\nЗапрос передан команде менеджеров."
                )
                await message.answer(
                    "Заявка сохранена. Я показал лучшие доступные варианты, а менеджер тоже увидит запрос и сможет помочь точнее."
                    + manager_hint,
                    keyboard=get_main_menu_keyboard(),
                )
            else:
                manager_hint = (
                    "\nМенеджер уже занимается вашим вопросом."
                    if assigned_manager_vk_id
                    else "\nЗапрос передан команде менеджеров."
                )
                await message.answer(
                    "Заявка сохранена и передана менеджеру для ручного подбора." + manager_hint,
                    keyboard=get_main_menu_keyboard(),
                )
            return

        if text == "изменить запрос":
            await _show_scope_step(bot, message)
            return

        await message.answer(
            "Выберите действие:\n"
            "- «Подтверждаю», если все верно\n"
            "- «Изменить запрос», если хотите заполнить заново",
            keyboard=get_request_confirmation_keyboard(),
        )
