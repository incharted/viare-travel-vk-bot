from datetime import date

from utils.validators import (
    MONTHS,
    normalize_country,
    parse_budget,
    parse_exact_date_range,
    parse_month_range,
    parse_travelers,
)


def test_parse_budget_accepts_human_formatting():
    assert parse_budget("400 000 руб.") == 400000
    assert parse_budget("от 150000") == 150000


def test_parse_budget_rejects_empty_or_unrealistic_values():
    assert parse_budget("abc") is None
    assert parse_budget("9999") is None
    assert parse_budget("25000000") is None


def test_parse_exact_date_range_returns_iso_dates():
    assert parse_exact_date_range("20.06.2026 - 27.06.2026") == (
        "2026-06-20",
        "2026-06-27",
    )


def test_parse_exact_date_range_rejects_invalid_order():
    assert parse_exact_date_range("27.06.2026 - 20.06.2026") is None


def test_parse_month_range_rolls_next_year_when_month_passed():
    may_name = next(name for name, number in MONTHS.items() if number == 5)

    assert parse_month_range(may_name, today=date(2026, 6, 1)) == (
        "2027-05-01",
        "2027-05-31",
    )


def test_parse_travelers_accepts_only_supported_group_size():
    assert parse_travelers("4") == 4
    assert parse_travelers("0") is None
    assert parse_travelers("16") is None
    assert parse_travelers("two") is None


def test_normalize_country_cleans_spaces_and_case():
    assert normalize_country("  egypt  ") == "Egypt"
    assert normalize_country("12345") is None
