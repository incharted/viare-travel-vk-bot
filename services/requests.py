from __future__ import annotations

from database.db import db

REQUEST_STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "waiting_client": "Ждет клиента",
    "answered": "Отвечена",
    "closed": "Закрыта",
}

_REQUEST_SELECT_SQL = """
    SELECT r.id, u.id AS user_id, u.vk_id, r.travel_scope, r.country, r.destination, r.budget,
           r.travelers, r.start_date, r.end_date, r.rest_type, r.status,
           r.manager_required, r.assigned_manager_vk_id,
           r.sla_15_sent, r.sla_30_sent, r.sla_60_sent,
           r.created_at, r.updated_at
    FROM requests r
    JOIN users u ON u.id = r.user_id
"""

_STATUS_ORDER_SQL = (
    "CASE r.status "
    "WHEN 'new' THEN 0 "
    "WHEN 'in_progress' THEN 1 "
    "WHEN 'waiting_client' THEN 2 "
    "WHEN 'answered' THEN 3 "
    "ELSE 4 END"
)


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
    query = _REQUEST_SELECT_SQL
    params: list[object] = []
    if status:
        query += " WHERE r.status = ?"
        params.append(status)
    query += f" ORDER BY {_STATUS_ORDER_SQL}, r.created_at DESC LIMIT ?;"
    params.append(limit)
    return await db.fetchall(query, tuple(params))


async def list_requests_for_export() -> list[dict]:
    return await db.fetchall(
        _REQUEST_SELECT_SQL + " ORDER BY r.created_at DESC;"
    )


async def get_request_by_id(request_id: int) -> dict | None:
    return await db.fetchone(
        _REQUEST_SELECT_SQL + " WHERE r.id = ?;",
        (request_id,),
    )


async def get_latest_request_by_vk_id(vk_id: int) -> dict | None:
    return await db.fetchone(
        _REQUEST_SELECT_SQL + " WHERE u.vk_id = ? ORDER BY r.created_at DESC LIMIT 1;",
        (vk_id,),
    )


async def get_latest_request_by_user_id(user_id: int) -> dict | None:
    return await db.fetchone(
        _REQUEST_SELECT_SQL + " WHERE u.id = ? ORDER BY r.created_at DESC LIMIT 1;",
        (user_id,),
    )


async def list_requests_by_user_id(user_id: int, limit: int = 10) -> list[dict]:
    return await db.fetchall(
        _REQUEST_SELECT_SQL + f" WHERE u.id = ? ORDER BY {_STATUS_ORDER_SQL}, r.created_at DESC LIMIT ?;",
        (user_id, limit),
    )


async def get_next_request(statuses: tuple[str, ...] = ("new", "in_progress")) -> dict | None:
    placeholders = ",".join("?" for _ in statuses)
    return await db.fetchone(
        _REQUEST_SELECT_SQL
        + f"""
        WHERE r.status IN ({placeholders})
        ORDER BY {_STATUS_ORDER_SQL}, CASE WHEN r.assigned_manager_vk_id IS NULL THEN 0 ELSE 1 END, r.created_at ASC
        LIMIT 1;
        """,
        statuses,
    )


async def get_next_request_for_staff(
    staff_vk_id: int,
    is_admin_role: bool,
    statuses: tuple[str, ...] = ("new", "in_progress", "waiting_client"),
) -> dict | None:
    placeholders = ",".join("?" for _ in statuses)
    if is_admin_role:
        return await db.fetchone(
            _REQUEST_SELECT_SQL
            + f"""
            WHERE r.status IN ({placeholders})
            ORDER BY {_STATUS_ORDER_SQL},
                     CASE WHEN r.assigned_manager_vk_id IS NULL THEN 0 ELSE 1 END,
                     r.created_at ASC
            LIMIT 1;
            """,
            statuses,
        )

    return await db.fetchone(
        _REQUEST_SELECT_SQL
        + f"""
        WHERE r.status IN ({placeholders})
          AND (r.assigned_manager_vk_id IS NULL OR r.assigned_manager_vk_id = ?)
        ORDER BY CASE WHEN r.assigned_manager_vk_id = ? THEN 0 ELSE 1 END,
                 {_STATUS_ORDER_SQL},
                 r.created_at ASC
        LIMIT 1;
        """,
        (*statuses, staff_vk_id, staff_vk_id),
    )


async def update_request_status(request_id: int, status: str) -> None:
    if status in {"new", "in_progress"}:
        await db.execute(
            """
            UPDATE requests
            SET status = ?, updated_at = CURRENT_TIMESTAMP,
                sla_15_sent = 0, sla_30_sent = 0, sla_60_sent = 0
            WHERE id = ?;
            """,
            (status, request_id),
        )
        return
    await db.execute(
        "UPDATE requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
        (status, request_id),
    )


async def assign_request_manager(request_id: int, manager_vk_id: int) -> None:
    await db.execute(
        """
        UPDATE requests
        SET assigned_manager_vk_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """,
        (manager_vk_id, request_id),
    )


async def unassign_request_manager(request_id: int) -> None:
    await db.execute(
        """
        UPDATE requests
        SET assigned_manager_vk_id = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """,
        (request_id,),
    )


async def list_requests_for_sla(
    statuses: tuple[str, ...] = ("new", "in_progress"),
    limit: int = 200,
) -> list[dict]:
    placeholders = ",".join("?" for _ in statuses)
    return await db.fetchall(
        _REQUEST_SELECT_SQL
        + f"""
        WHERE r.status IN ({placeholders})
          AND (r.sla_15_sent = 0 OR r.sla_30_sent = 0 OR r.sla_60_sent = 0)
        ORDER BY r.created_at ASC
        LIMIT ?;
        """,
        (*statuses, limit),
    )


async def mark_sla_reminder_sent(request_id: int, threshold_minutes: int) -> None:
    if threshold_minutes == 15:
        column = "sla_15_sent"
    elif threshold_minutes == 30:
        column = "sla_30_sent"
    elif threshold_minutes == 60:
        column = "sla_60_sent"
    else:
        raise ValueError("Unsupported SLA threshold")

    await db.execute(
        f"UPDATE requests SET {column} = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
        (request_id,),
    )
