from __future__ import annotations

from database.db import db


async def get_stats() -> dict:
    users = await db.fetchone("SELECT COUNT(*) AS c FROM users;")
    requests = await db.fetchone("SELECT COUNT(*) AS c FROM requests;")
    logs = await db.fetchone("SELECT COUNT(*) AS c FROM logs;")
    tours = await db.fetchone("SELECT COUNT(*) AS c FROM tours WHERE is_active = 1;")

    return {
        "users": users["c"] if users else 0,
        "requests": requests["c"] if requests else 0,
        "logs": logs["c"] if logs else 0,
        "tours": tours["c"] if tours else 0,
    }


async def get_sales_analytics(top_limit: int = 5) -> dict:
    summary = await db.fetchone(
        """
        SELECT
            COUNT(*) AS total_requests,
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS new_requests,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_requests,
            SUM(CASE WHEN status = 'waiting_client' THEN 1 ELSE 0 END) AS waiting_client_requests,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_requests,
            ROUND(AVG(CASE WHEN budget > 0 THEN budget END), 0) AS avg_budget
        FROM requests;
        """
    ) or {}

    total_requests = int(summary.get("total_requests") or 0)
    closed_requests = int(summary.get("closed_requests") or 0)
    conversion_closed_pct = round((closed_requests / total_requests) * 100, 1) if total_requests > 0 else 0.0

    top_destinations = await db.fetchall(
        """
        SELECT COALESCE(NULLIF(destination, ''), NULLIF(country, ''), 'Без направления') AS destination,
               COUNT(*) AS requests_count
        FROM requests
        GROUP BY COALESCE(NULLIF(destination, ''), NULLIF(country, ''), 'Без направления')
        ORDER BY requests_count DESC, destination ASC
        LIMIT ?;
        """,
        (top_limit,),
    )

    manager_load = await db.fetchall(
        """
        SELECT assigned_manager_vk_id AS manager_vk_id, COUNT(*) AS requests_count
        FROM requests
        WHERE assigned_manager_vk_id IS NOT NULL
        GROUP BY assigned_manager_vk_id
        ORDER BY requests_count DESC, manager_vk_id ASC
        LIMIT ?;
        """,
        (top_limit,),
    )

    return {
        "total_requests": total_requests,
        "new_requests": int(summary.get("new_requests") or 0),
        "in_progress_requests": int(summary.get("in_progress_requests") or 0),
        "waiting_client_requests": int(summary.get("waiting_client_requests") or 0),
        "closed_requests": closed_requests,
        "avg_budget": int(summary.get("avg_budget") or 0),
        "conversion_closed_pct": conversion_closed_pct,
        "top_destinations": top_destinations,
        "manager_load": manager_load,
    }


async def add_log(user_id: int | None, event_type: str, message: str, level: str = "INFO") -> int:
    return await db.execute(
        "INSERT INTO logs (user_id, event_type, message, level) VALUES (?, ?, ?, ?);",
        (user_id, event_type, message, level),
    )
