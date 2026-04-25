from __future__ import annotations

from datetime import date

from vkbottle import Keyboard, KeyboardButtonColor, Text

MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def _chunked_keyboard(items: list[str], per_row: int = 3, one_time: bool = True) -> Keyboard:
    keyboard = Keyboard(one_time=one_time, inline=False)
    for index, item in enumerate(items, start=1):
        keyboard.add(Text(item), color=KeyboardButtonColor.PRIMARY)
        if index % per_row == 0 and index != len(items):
            keyboard.row()
    return keyboard


def get_main_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("Подобрать тур"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Все туры"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Мой статус"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Избранное"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("Как пользоваться"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("FAQ"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Контакты"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Оплата и бронирование"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("Услуги VIARE Travel"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("О VIARE Travel"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("Связаться с менеджером"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()


def get_welcome_keyboard() -> str:
    keyboard = Keyboard(one_time=True, inline=False)
    keyboard.add(Text("Что умеет бот?"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Как пользоваться"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_staff_menu_keyboard(role: str) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("Заявки"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Следующая заявка"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("Новые"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("В работе"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Ждут клиента"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("Закрытые"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Карточка заявки"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Ответ по заявке"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("Закрепить заявку"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Шаблон ответа"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Шаблоны ответов"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("Закрыть заявку"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Календарь менеджеров"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Помощь по панели"), color=KeyboardButtonColor.SECONDARY)

    if role == "admin":
        keyboard.add(Text("Статистика"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Пользователи"), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
        keyboard.add(Text("Выгрузка заявок"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Туры админ"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Менеджеры"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Добавить менеджера"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Убрать менеджера"), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
        keyboard.add(Text("Как назначить менеджера"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("PDF КП"), color=KeyboardButtonColor.POSITIVE)
        keyboard.add(Text("FAQ текст"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Контакты текст"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Оплата текст"), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
        keyboard.add(Text("Разблокировать VK"), color=KeyboardButtonColor.SECONDARY)
        keyboard.add(Text("Рассылка"), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
    else:
        keyboard.row()

    keyboard.add(Text("Выйти из панели"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()


def get_back_to_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_rest_type_keyboard() -> str:
    keyboard = Keyboard(one_time=True, inline=False)
    keyboard.add(Text("Любой тип отдыха"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("пляжный"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("экскурсионный"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("активный"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("семейный"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("горнолыжный"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("оздоровительный"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_destination_scope_keyboard() -> str:
    keyboard = Keyboard(one_time=True, inline=False)
    keyboard.add(Text("По России"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("За границу"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_country_keyboard(countries: list[str]) -> str:
    keyboard = _chunked_keyboard(countries, per_row=3, one_time=True)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_domestic_destination_keyboard(destinations: list[str]) -> str:
    keyboard = _chunked_keyboard(destinations, per_row=2, one_time=True)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_month_keyboard() -> str:
    today = date.today()
    labels: list[str] = []
    month = today.month
    year = today.year
    for _ in range(8):
        labels.append(f"{MONTH_NAMES[month]} {year}")
        month += 1
        if month > 12:
            month = 1
            year += 1

    keyboard = _chunked_keyboard(labels, per_row=2, one_time=True)
    keyboard.row()
    keyboard.add(Text("Точные даты"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_request_confirmation_keyboard() -> str:
    keyboard = Keyboard(one_time=True, inline=False)
    keyboard.add(Text("Подтверждаю"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Изменить запрос"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("В меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()
