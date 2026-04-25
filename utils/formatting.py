from __future__ import annotations

from collections import defaultdict

from services.requests import request_status_label


def _format_price(value: int | None) -> str:
    if value is None:
        return "не указан"
    return f"{value:,}".replace(",", " ")


def format_tour_card(tour: dict, travelers: int) -> str:
    total_price = int(tour["price_per_person"]) * travelers
    destination = tour.get("destination") or tour["country"]
    price_per_person_text = _format_price(int(tour["price_per_person"]))
    total_price_text = _format_price(total_price)
    lines = [
        f"ТУР: {tour['name']}",
        "------------------------------",
        f"ID тура: {tour.get('id', '-')}",
        f"Направление: {destination}",
        f"Формат отдыха: {tour['rest_type']}",
        f"Длительность: {tour['duration_days']} дн.",
        f"Цена за человека: {price_per_person_text} ₽",
        f"Итого на {travelers} чел.: {total_price_text} ₽",
        "",
        "Описание:",
        f"{tour['description']}",
    ]

    if tour.get("checkin_date"):
        lines.extend(["", f"Ближайший заезд: {tour['checkin_date']}"])
    if tour.get("source"):
        lines.append(f"Источник: {tour['source']}")
    if tour.get("tour_page_url"):
        lines.append(f"Ссылка на тур: {tour['tour_page_url']}")
    elif tour.get("search_page_url"):
        lines.append(f"Ссылка на подборку: {tour['search_page_url']}")

    return "\n".join(lines)


def build_tour_catalog_messages(tours: list[dict], max_len: int = 3500) -> list[str]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for tour in tours:
        grouped[str(tour["rest_type"])].append(tour)

    sections: list[str] = []
    for rest_type in sorted(grouped):
        lines = [f"{rest_type.capitalize()} туры"]
        for index, tour in enumerate(
            sorted(
                grouped[rest_type],
                key=lambda item: (
                    str(item.get("travel_scope") or ""),
                    str(item.get("country") or ""),
                    str(item.get("destination") or ""),
                    int(item.get("price_per_person") or 0),
                ),
            ),
            start=1,
        ):
            destination = str(tour.get("destination") or tour["country"])
            lines.append(
                f"{index}. [{tour.get('id', '-')}] {tour['name']}\n"
                f"   {destination} | {tour['duration_days']} дн. | от {_format_price(int(tour['price_per_person']))} ₽/чел.\n"
                f"   {tour['description']}"
            )
        sections.append("\n\n".join(lines))

    messages: list[str] = []
    current = (
        "Каталог туров VIARE Travel\n"
        "Подсказка: чтобы сохранить тур, используйте /fav (потом введите ID тура).\n"
    )
    for section in sections:
        block = f"\n\n{section}"
        if len(current) + len(block) > max_len:
            messages.append(current.rstrip())
            current = "Каталог туров VIARE Travel\n"
        current += block

    if current.strip():
        messages.append(current.rstrip())

    return messages


def format_request_summary_for_confirmation(payload: dict) -> str:
    if payload.get("travel_scope") == "domestic":
        scope_label = "По России"
    elif payload.get("travel_scope") == "abroad":
        scope_label = "За границу"
    else:
        scope_label = "Не указан"
    destination = payload.get("destination") or payload.get("country") or "не указано"
    rest_type = payload.get("rest_type") or "не указан"
    if rest_type == "any":
        rest_type = "любой"
    return (
        "ПРОВЕРЬТЕ ЗАЯВКУ ПЕРЕД ОТПРАВКОЙ\n"
        "------------------------------\n"
        f"Формат поездки: {scope_label}\n"
        f"Направление: {destination}\n"
        f"Бюджет: {_format_price(payload.get('budget'))} ₽\n"
        f"Туристов: {payload.get('travelers') or 'не указано'}\n"
        f"Даты: {payload.get('start_date')} - {payload.get('end_date')}\n"
        f"Тип отдыха: {rest_type}"
    )


def format_request_card(request: dict) -> str:
    destination = request.get("destination") or request.get("country") or "не указано"
    if request.get("travel_scope") == "domestic":
        scope_label = "По России"
    elif request.get("travel_scope") == "abroad":
        scope_label = "За границу"
    else:
        scope_label = "Не указан"
    manager_text = "Да" if int(request.get("manager_required") or 0) == 1 else "Нет"
    assigned_manager_vk_id = request.get("assigned_manager_vk_id")
    assigned_text = f"vk={assigned_manager_vk_id}" if assigned_manager_vk_id else "не назначен"
    rest_type = request.get("rest_type") or "не указан"
    if rest_type == "any":
        rest_type = "любой"
    return (
        f"ЗАЯВКА #{request['id']}\n"
        "------------------------------\n"
        f"Статус: {request_status_label(str(request.get('status') or ''))}\n"
        f"Клиент VK: {request['vk_id']}\n"
        f"Формат поездки: {scope_label}\n"
        f"Направление: {destination}\n"
        f"Бюджет: {_format_price(request.get('budget'))} ₽\n"
        f"Туристов: {request.get('travelers') or 'не указано'}\n"
        f"Даты: {request.get('start_date') or 'не указаны'} - {request.get('end_date') or 'не указаны'}\n"
        f"Тип отдыха: {rest_type}\n"
        f"Нужен менеджер: {manager_text}\n"
        f"Ответственный менеджер: {assigned_text}\n"
        "------------------------------\n"
        f"Создана: {request.get('created_at')}\n"
        f"Обновлена: {request.get('updated_at') or request.get('created_at')}"
    )


def format_request_list_item(request: dict) -> str:
    destination = request.get("destination") or request.get("country") or "без направления"
    budget = f"{_format_price(request.get('budget'))} ₽" if request.get("budget") else "не указан"
    travelers = request.get("travelers") or "-"
    assignee = (
        f"mgr={request.get('assigned_manager_vk_id')}"
        if request.get("assigned_manager_vk_id")
        else "mgr=free"
    )
    return (
        f"#{request['id']} | {request_status_label(str(request.get('status') or ''))} | "
        f"{destination} | бюджет {budget} | {travelers} чел. | vk={request['vk_id']} | {assignee}"
    )


def format_request_notification(
    request_id: int,
    user_vk_id: int,
    country: str | None,
    budget: int | None,
    travelers: int | None,
    start_date: str | None,
    end_date: str | None,
    rest_type: str | None,
    manager_required: bool,
    travel_scope: str | None = None,
    destination: str | None = None,
    status: str = "new",
) -> str:
    if travel_scope == "domestic":
        scope_label = "По России"
    elif travel_scope == "abroad":
        scope_label = "За границу"
    else:
        scope_label = "Не указан"
    destination_text = destination or country or "не указано"
    rest_text = rest_type or "не указан"
    if rest_text == "any":
        rest_text = "любой"
    return (
        f"Новая заявка #{request_id}\n"
        f"Статус: {request_status_label(status)}\n"
        f"Клиент VK: {user_vk_id}\n"
        f"Формат поездки: {scope_label}\n"
        f"Направление: {destination_text}\n"
        f"Страна: {country or 'не указана'}\n"
        f"Бюджет: {_format_price(budget)} ₽\n"
        f"Туристы: {travelers or 'не указано'}\n"
        f"Даты: {start_date or 'не указаны'} - {end_date or 'не указаны'}\n"
        f"Тип отдыха: {rest_text}\n"
        f"Нужен менеджер: {'Да' if manager_required else 'Нет'}\n"
        "Команда для ответа:\n"
        "/request_assign\n"
        f"{request_id}\n"
        "или\n"
        "/reply_request\n"
        f"{request_id} | Здравствуйте! Подобрал варианты по вашему запросу."
    )
