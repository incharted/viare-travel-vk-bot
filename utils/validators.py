from __future__ import annotations

import calendar
import re
from datetime import date, datetime

COUNTRY_RE = re.compile(r"^[A-Za-zА-Яа-яЁё\-\s]{2,60}$")
DATE_RANGE_RE = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})$")
MONTH_RE = re.compile(
    r"^(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)(?:\s+(\d{4}))?$",
    re.IGNORECASE,
)

REST_TYPES = {
    "любой тип отдыха": "any",
    "пляжный": "пляжный",
    "экскурсионный": "экскурсионный",
    "активный": "активный",
    "семейный": "семейный",
    "горнолыжный": "горнолыжный",
    "оздоровительный": "оздоровительный",
}

MONTHS = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
}


def normalize_country(value: str) -> str | None:
    text = value.strip()
    if not COUNTRY_RE.match(text):
        return None
    return " ".join(part.capitalize() for part in text.split())


def parse_budget(value: str) -> int | None:
    cleaned = re.sub(r"[^0-9]", "", value)
    if not cleaned:
        return None
    budget = int(cleaned)
    if budget < 10000 or budget > 20_000_000:
        return None
    return budget


def parse_exact_date_range(value: str) -> tuple[str, str] | None:
    match = DATE_RANGE_RE.match(value.strip())
    if not match:
        return None

    start_str, end_str = match.groups()
    try:
        start = datetime.strptime(start_str, "%d.%m.%Y")
        end = datetime.strptime(end_str, "%d.%m.%Y")
    except ValueError:
        return None

    if end < start:
        return None

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def parse_month_range(value: str, today: date | None = None) -> tuple[str, str] | None:
    match = MONTH_RE.match(value.strip().lower())
    if not match:
        return None

    month_name, year_text = match.groups()
    month = MONTHS[month_name]
    base_today = today or date.today()
    year = int(year_text) if year_text else base_today.year
    if not year_text and month < base_today.month:
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def parse_date_range(value: str) -> tuple[str, str] | None:
    return parse_exact_date_range(value) or parse_month_range(value)


def parse_travelers(value: str) -> int | None:
    if not value.strip().isdigit():
        return None
    travelers = int(value.strip())
    if travelers < 1 or travelers > 15:
        return None
    return travelers


def normalize_rest_type(value: str) -> str | None:
    text = value.strip().lower()
    return REST_TYPES.get(text)
