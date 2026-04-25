from __future__ import annotations

from database.db import db


async def add_favorite_tour(user_id: int, tour_id: int) -> bool:
    tour = await db.fetchone("SELECT id FROM tours WHERE id = ? AND is_active = 1;", (tour_id,))
    if not tour:
        return False
    await db.execute(
        """
        INSERT INTO user_favorite_tours (user_id, tour_id)
        VALUES (?, ?)
        ON CONFLICT(user_id, tour_id) DO NOTHING;
        """,
        (user_id, tour_id),
    )
    return True


async def remove_favorite_tour(user_id: int, tour_id: int) -> bool:
    existing = await db.fetchone(
        "SELECT 1 AS e FROM user_favorite_tours WHERE user_id = ? AND tour_id = ?;",
        (user_id, tour_id),
    )
    if not existing:
        return False
    await db.execute(
        "DELETE FROM user_favorite_tours WHERE user_id = ? AND tour_id = ?;",
        (user_id, tour_id),
    )
    return True


async def list_favorite_tours(user_id: int, limit: int = 20) -> list[dict]:
    return await db.fetchall(
        """
        SELECT t.*, f.created_at AS favorited_at
        FROM user_favorite_tours f
        JOIN tours t ON t.id = f.tour_id
        WHERE f.user_id = ?
          AND t.is_active = 1
        ORDER BY f.created_at DESC
        LIMIT ?;
        """,
        (user_id, limit),
    )


async def count_favorite_tours(user_id: int) -> int:
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM user_favorite_tours WHERE user_id = ?;",
        (user_id,),
    )
    return int((row or {}).get("c") or 0)
