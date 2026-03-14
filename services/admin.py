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


async def add_log(user_id: int | None, event_type: str, message: str, level: str = "INFO") -> int:
    return await db.execute(
        "INSERT INTO logs (user_id, event_type, message, level) VALUES (?, ?, ?, ?);",
        (user_id, event_type, message, level),
    )
