from __future__ import annotations

from database.db import db

REQUEST_STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "waiting_client": "Ждет клиента",
    "answered": "Отвечена",
    "closed": "Закрыта",
}


def request_status_label(status: str | None) -> str:
    if not status:
        return "Не указан"
    return REQUEST_STATUS_LABELS.get(status, status)


async def create_request(
    user_id: int,
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
) -> int:
    return await db.execute(
        """
        INSERT INTO requests (
            user_id, travel_scope, country, destination, budget, travelers,
            start_date, end_date, rest_type, status, manager_required, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """,
        (
            user_id,
            travel_scope,
            country,
            destination,
            budget,
            travelers,
            start_date,
            end_date,
            rest_type,
            status,
            1 if manager_required else 0,
        ),
    )


async def list_requests(limit: int = 20, status: str | None = None) -> list[dict]:
    query = """
        SELECT r.id, u.id AS user_id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
               r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
               r.manager_required, r.created_at, r.updated_at
        FROM requests r
        JOIN users u ON u.id = r.user_id
    """
    params: list[object] = []
    if status:
        query += " WHERE r.status = ?"
        params.append(status)
    query += " ORDER BY r.created_at DESC LIMIT ?;"
    params.append(limit)
    return await db.fetchall(query, tuple(params))


async def list_requests_for_export() -> list[dict]:
    return await db.fetchall(
        """
        SELECT r.id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
               r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
               r.manager_required, r.created_at, r.updated_at
        FROM requests r
        JOIN users u ON u.id = r.user_id
        ORDER BY r.created_at DESC;
        """
    )


async def get_request_by_id(request_id: int) -> dict | None:
    return await db.fetchone(
        """
        SELECT r.id, u.id AS user_id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
               r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
               r.manager_required, r.created_at, r.updated_at
        FROM requests r
        JOIN users u ON u.id = r.user_id
        WHERE r.id = ?;
        """,
        (request_id,),
    )


async def get_latest_request_by_vk_id(vk_id: int) -> dict | None:
    return await db.fetchone(
        """
        SELECT r.id, u.id AS user_id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
               r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
               r.manager_required, r.created_at, r.updated_at
        FROM requests r
        JOIN users u ON u.id = r.user_id
        WHERE u.vk_id = ?
        ORDER BY r.created_at DESC
        LIMIT 1;
        """,
        (vk_id,),
    )


async def get_next_request(statuses: tuple[str, ...] = ("new", "in_progress")) -> dict | None:
    placeholders = ",".join("?" for _ in statuses)
    return await db.fetchone(
        f"""
        SELECT r.id, u.id AS user_id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
               r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
               r.manager_required, r.created_at, r.updated_at
        FROM requests r
        JOIN users u ON u.id = r.user_id
        WHERE r.status IN ({placeholders})
        ORDER BY CASE r.status WHEN 'new' THEN 0 WHEN 'in_progress' THEN 1 WHEN 'waiting_client' THEN 2 ELSE 3 END,
                 r.created_at ASC
        LIMIT 1;
        """,
        statuses,
    )


async def update_request_status(request_id: int, status: str) -> None:
    await db.execute(
        "UPDATE requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
        (status, request_id),
    )
