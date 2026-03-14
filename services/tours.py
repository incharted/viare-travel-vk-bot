from __future__ import annotations

from database.db import db


def _apply_destination_filter(query: str, params: list[object], travel_scope: str, destination: str | None) -> str:
    if destination and travel_scope.lower() == "domestic":
        query += " AND (lower(COALESCE(destination, '')) = lower(?) OR destination IS NULL)"
        params.append(destination)
    return query


async def find_tours(
    travel_scope: str,
    country: str,
    destination: str | None,
    budget: int,
    travelers: int,
    start_date: str,
    end_date: str,
    rest_type: str,
    limit: int = 5,
) -> list[dict]:
    query = """
        SELECT *
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = lower(?)
          AND lower(country) = lower(?)
          AND (? BETWEEN available_from AND available_to)
          AND (? BETWEEN available_from AND available_to)
          AND price_per_person * ? <= ?
    """
    params: list[object] = [travel_scope, country, start_date, end_date, travelers, budget]
    if rest_type != "any":
        query += " AND lower(rest_type) = lower(?)"
        params.append(rest_type)

    query = _apply_destination_filter(query, params, travel_scope, destination)
    query += " ORDER BY price_per_person ASC LIMIT ?;"
    params.append(limit)
    return await db.fetchall(query, tuple(params))


async def find_tours_flexible(
    travel_scope: str,
    country: str,
    destination: str | None,
    budget: int,
    travelers: int,
    start_date: str,
    end_date: str,
    rest_type: str,
    limit: int = 5,
) -> list[dict]:
    rest_rank_sql = "0" if rest_type == "any" else "CASE WHEN lower(rest_type) = lower(?) THEN 0 ELSE 1 END"
    query = f"""
        SELECT *,
               {rest_rank_sql} AS rest_rank,
               CASE
                   WHEN (? BETWEEN available_from AND available_to)
                    AND (? BETWEEN available_from AND available_to) THEN 0
                   ELSE 1
               END AS date_rank
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = lower(?)
          AND lower(country) = lower(?)
          AND price_per_person * ? <= ?
    """
    params: list[object] = []
    if rest_type != "any":
        params.append(rest_type)
    params.extend([start_date, end_date, travel_scope, country, travelers, budget])
    query = _apply_destination_filter(query, params, travel_scope, destination)
    query += " ORDER BY date_rank ASC, rest_rank ASC, price_per_person ASC LIMIT ?;"
    params.append(limit)
    return await db.fetchall(query, tuple(params))


async def find_cheapest_destination_tours(
    travel_scope: str,
    country: str,
    destination: str | None,
    travelers: int,
    limit: int = 5,
) -> list[dict]:
    query = """
        SELECT *
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = lower(?)
          AND lower(country) = lower(?)
    """
    params: list[object] = [travel_scope, country]
    query = _apply_destination_filter(query, params, travel_scope, destination)
    query += " ORDER BY price_per_person ASC, available_from ASC LIMIT ?;"
    params.append(limit)
    return await db.fetchall(query, tuple(params))


async def get_destination_availability(
    travel_scope: str,
    country: str,
    destination: str | None,
    travelers: int = 1,
) -> dict | None:
    query = """
        SELECT MIN(price_per_person) AS min_price_per_person,
               MIN(available_from) AS min_available_from,
               MAX(available_to) AS max_available_to,
               COUNT(*) AS tours_count
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = lower(?)
          AND lower(country) = lower(?)
    """
    params: list[object] = [travel_scope, country]
    query = _apply_destination_filter(query, params, travel_scope, destination)
    summary = await db.fetchone(query + ";", tuple(params))
    if not summary or not summary.get("tours_count"):
        return None

    rest_types_query = """
        SELECT DISTINCT rest_type
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = lower(?)
          AND lower(country) = lower(?)
    """
    rest_params: list[object] = [travel_scope, country]
    rest_types_query = _apply_destination_filter(rest_types_query, rest_params, travel_scope, destination)
    rest_types_query += " ORDER BY rest_type ASC;"

    rest_rows = await db.fetchall(rest_types_query, tuple(rest_params))
    min_price_per_person = int(summary["min_price_per_person"] or 0)
    return {
        "min_price_per_person": min_price_per_person,
        "min_total_price": min_price_per_person * travelers if min_price_per_person else None,
        "min_available_from": summary.get("min_available_from"),
        "max_available_to": summary.get("max_available_to"),
        "tours_count": int(summary["tours_count"] or 0),
        "rest_types": [str(row["rest_type"]) for row in rest_rows if row.get("rest_type")],
    }


async def list_tours(limit: int = 20) -> list[dict]:
    return await db.fetchall(
        """
        SELECT *
        FROM tours
        WHERE is_active = 1
        ORDER BY travel_scope, country, destination, price_per_person
        LIMIT ?;
        """,
        (limit,),
    )


async def list_available_countries(limit: int = 30) -> list[str]:
    rows = await db.fetchall(
        """
        SELECT DISTINCT country
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = 'abroad'
        ORDER BY country ASC
        LIMIT ?;
        """,
        (limit,),
    )
    return [str(row["country"]) for row in rows if row.get("country")]


async def list_domestic_destinations(limit: int = 30) -> list[str]:
    rows = await db.fetchall(
        """
        SELECT DISTINCT destination
        FROM tours
        WHERE is_active = 1
          AND lower(travel_scope) = 'domestic'
          AND destination IS NOT NULL
          AND trim(destination) != ''
        ORDER BY destination ASC
        LIMIT ?;
        """,
        (limit,),
    )
    return [str(row["destination"]) for row in rows if row.get("destination")]


async def list_tours_admin(limit: int = 100) -> list[dict]:
    return await db.fetchall(
        """
        SELECT *
        FROM tours
        ORDER BY is_active DESC, travel_scope, country, destination, price_per_person
        LIMIT ?;
        """,
        (limit,),
    )


async def get_tour_by_id(tour_id: int) -> dict | None:
    return await db.fetchone("SELECT * FROM tours WHERE id = ?;", (tour_id,))


async def create_tour(
    name: str,
    country: str,
    price_per_person: int,
    duration_days: int,
    rest_type: str,
    available_from: str,
    available_to: str,
    description: str,
    photo_url: str | None = None,
    destination: str | None = None,
    travel_scope: str | None = None,
) -> int:
    resolved_scope = travel_scope or ("domestic" if country.lower() == "россия" else "abroad")
    return await db.execute(
        """
        INSERT INTO tours (
            name, country, destination, travel_scope, price_per_person, duration_days, rest_type,
            available_from, available_to, description, photo_url, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
        """,
        (
            name,
            country,
            destination,
            resolved_scope,
            price_per_person,
            duration_days,
            rest_type,
            available_from,
            available_to,
            description,
            photo_url,
        ),
    )


async def set_tour_active(tour_id: int, is_active: bool) -> None:
    await db.execute(
        "UPDATE tours SET is_active = ? WHERE id = ?;",
        (1 if is_active else 0, tour_id),
    )


async def update_tour_price(tour_id: int, price_per_person: int) -> None:
    await db.execute(
        "UPDATE tours SET price_per_person = ? WHERE id = ?;",
        (price_per_person, tour_id),
    )
