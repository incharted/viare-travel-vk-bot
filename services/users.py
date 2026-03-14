from __future__ import annotations

from database.db import db


async def upsert_user(vk_id: int, is_admin: bool = False, is_manager: bool = False) -> int:
    existing = await db.fetchone("SELECT id FROM users WHERE vk_id = ?;", (vk_id,))
    if existing:
        if is_admin or is_manager:
            await db.execute(
                """
                UPDATE users
                SET is_admin = CASE WHEN ? = 1 THEN 1 ELSE is_admin END,
                    is_manager = CASE WHEN ? = 1 THEN 1 ELSE is_manager END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE vk_id = ?;
                """,
                (1 if is_admin else 0, 1 if is_manager else 0, vk_id),
            )
        else:
            await db.execute(
                "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE vk_id = ?;",
                (vk_id,),
            )
        return int(existing["id"])

    return await db.execute(
        "INSERT INTO users (vk_id, is_admin, is_manager) VALUES (?, ?, ?);",
        (vk_id, 1 if is_admin else 0, 1 if is_manager else 0),
    )


async def get_user_by_vk_id(vk_id: int) -> dict | None:
    return await db.fetchone("SELECT * FROM users WHERE vk_id = ?;", (vk_id,))


async def list_users(limit: int = 20) -> list[dict]:
    return await db.fetchall(
        "SELECT id, vk_id, is_admin, is_manager, created_at FROM users ORDER BY created_at DESC LIMIT ?;",
        (limit,),
    )


async def list_admin_vk_ids() -> list[int]:
    rows = await db.fetchall("SELECT vk_id FROM users WHERE is_admin = 1 ORDER BY vk_id;")
    return [int(row["vk_id"]) for row in rows]


async def list_manager_vk_ids() -> list[int]:
    rows = await db.fetchall("SELECT vk_id FROM users WHERE is_manager = 1 ORDER BY vk_id;")
    return [int(row["vk_id"]) for row in rows]
