from __future__ import annotations

import logging
from datetime import datetime, timedelta

import aiohttp

from config import get_settings

logger = logging.getLogger(__name__)


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def _parse_trip_dates(start_date: str, end_date: str) -> tuple[str, str, int, int]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end < start:
        end = start

    max_window_end = start + timedelta(days=29)
    checkin_to = min(end, max_window_end)
    trip_nights = max(4, (end - start).days or 7)
    nights_from = max(4, min(21, trip_nights - 2))
    nights_to = max(nights_from, min(21, trip_nights + 2))
    return start.isoformat(), checkin_to.isoformat(), nights_from, nights_to


async def _request_json(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, str] | list[tuple[str, str]],
) -> dict:
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        return await response.json()


async def _resolve_country_id(session: aiohttp.ClientSession, base_url: str, country: str) -> int | None:
    payload = await _request_json(session, f"{base_url}/directory/countries", {})
    for item in payload.get("data", []):
        name = str(item.get("name", ""))
        if _normalize_name(name) == _normalize_name(country):
            country_id = item.get("id")
            if isinstance(country_id, int):
                return country_id
    return None


async def fetch_external_offers(
    country: str,
    budget: int,
    travelers: int,
    start_date: str,
    end_date: str,
    rest_type: str,
) -> list[dict]:
    settings = get_settings()
    if not settings.external_tours_enabled:
        return []

    try:
        checkin_from, checkin_to, nights_from, nights_to = _parse_trip_dates(start_date, end_date)
    except ValueError:
        logger.warning("External offers skipped because dates are invalid: %s - %s", start_date, end_date)
        return []

    timeout = aiohttp.ClientTimeout(total=settings.travelata_timeout_sec)
    headers = {"User-Agent": "VIARE-Travel-Bot/1.0"}

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            country_id = await _resolve_country_id(session, settings.travelata_base_url, country)
            if country_id is None:
                logger.info("Travelata country not found for query: %s", country)
                return []

            params: list[tuple[str, str]] = [
                ("countries[]", str(country_id)),
                ("departureCity", str(settings.travelata_departure_city_id)),
                ("nightRange[from]", str(nights_from)),
                ("nightRange[to]", str(nights_to)),
                ("touristGroup[adults]", str(travelers)),
                ("touristGroup[kids]", "0"),
                ("touristGroup[infants]", "0"),
                ("checkInDateRange[from]", checkin_from),
                ("checkInDateRange[to]", checkin_to),
            ]
            payload = await _request_json(
                session,
                f"{settings.travelata_base_url}/statistic/cheapestTours",
                params,
            )
    except aiohttp.ClientError as err:
        logger.warning("Travelata request failed: %s", err)
        return []
    except Exception as err:  # noqa: BLE001
        logger.exception("Unexpected error while fetching external offers: %s", err)
        return []

    offers: list[dict] = []
    for item in payload.get("data", []):
        try:
            total_price = int(item.get("price") or 0)
        except (TypeError, ValueError):
            continue

        if total_price <= 0 or total_price > budget:
            continue

        nights = int(item.get("nights") or 0)
        price_per_person = max(1, total_price // max(travelers, 1))
        hotel_name = str(item.get("hotelName") or f"Тур в {country}")
        hotel_category = str(item.get("hotelCategoryName") or "").strip()
        hotel_rating = str(item.get("hotelRating") or "").strip()
        checkin_date = str(item.get("checkinDate") or "").strip()
        hotel_preview = str(item.get("hotelPreview") or "").strip()
        details: list[str] = ["Подтянуто из Travelata"]
        if hotel_category:
            details.append(f"Категория: {hotel_category}")
        if hotel_rating:
            details.append(f"Рейтинг: {hotel_rating}")
        if checkin_date:
            details.append(f"Заезд: {checkin_date}")

        search_url = str(item.get("searchPageUrl") or "").strip()
        tour_url = str(item.get("tourPageUrl") or "").strip()

        offers.append(
            {
                "name": hotel_name,
                "country": country,
                "price_per_person": price_per_person,
                "duration_days": max(1, nights),
                "rest_type": rest_type,
                "description": " | ".join(details),
                "source": "Travelata",
                "checkin_date": checkin_date,
                "search_page_url": search_url,
                "tour_page_url": tour_url,
                "photo_url": hotel_preview,
            }
        )

        if len(offers) >= settings.travelata_max_results:
            break

    return offers
