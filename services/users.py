from __future__ import annotations

from datetime import datetime, timedelta

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
        """
        SELECT id, vk_id, is_admin, is_manager, is_blocked, blocked_until, block_reason, spam_strikes, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT ?;
        """,
        (limit,),
    )


async def set_manager_role(vk_id: int, is_manager: bool) -> None:
    existing = await get_user_by_vk_id(vk_id)
    if not existing:
        await upsert_user(vk_id, is_manager=is_manager)
        return

    await db.execute(
        """
        UPDATE users
        SET is_manager = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (1 if is_manager else 0, vk_id),
    )


async def set_admin_role(vk_id: int, is_admin: bool) -> None:
    existing = await get_user_by_vk_id(vk_id)
    if not existing:
        await upsert_user(vk_id, is_admin=is_admin)
        return

    await db.execute(
        """
        UPDATE users
        SET is_admin = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (1 if is_admin else 0, vk_id),
    )


async def list_admin_vk_ids() -> list[int]:
    rows = await db.fetchall("SELECT vk_id FROM users WHERE is_admin = 1 ORDER BY vk_id;")
    return [int(row["vk_id"]) for row in rows]


async def list_manager_vk_ids() -> list[int]:
    rows = await db.fetchall("SELECT vk_id FROM users WHERE is_manager = 1 ORDER BY vk_id;")
    return [int(row["vk_id"]) for row in rows]


async def list_managers(limit: int = 100) -> list[dict]:
    return await db.fetchall(
        """
        SELECT id, vk_id, is_admin, is_manager, is_blocked, blocked_until, spam_strikes, last_assigned_at, created_at, updated_at
        FROM users
        WHERE is_manager = 1 OR is_admin = 1
        ORDER BY is_admin DESC, updated_at DESC
        LIMIT ?;
        """,
        (limit,),
    )


async def touch_manager_assignment(vk_id: int) -> None:
    await db.execute(
        """
        UPDATE users
        SET last_assigned_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (vk_id,),
    )


async def increment_spam_strike(vk_id: int) -> int:
    await db.execute(
        """
        UPDATE users
        SET spam_strikes = COALESCE(spam_strikes, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (vk_id,),
    )
    row = await get_user_by_vk_id(vk_id)
    return int((row or {}).get("spam_strikes") or 0)


async def reset_spam_strikes(vk_id: int) -> None:
    await db.execute(
        """
        UPDATE users
        SET spam_strikes = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (vk_id,),
    )


async def set_user_block(vk_id: int, is_blocked: bool, reason: str | None = None, duration_min: int | None = None) -> None:
    if is_blocked:
        blocked_until = None
        if duration_min and duration_min > 0:
            blocked_until = (datetime.now() + timedelta(minutes=duration_min)).isoformat(timespec="seconds")
        await db.execute(
            """
            UPDATE users
            SET is_blocked = 1,
                blocked_until = ?,
                block_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE vk_id = ?;
            """,
            (blocked_until, reason or "suspicious_activity", vk_id),
        )
        return

    await db.execute(
        """
        UPDATE users
        SET is_blocked = 0,
            blocked_until = NULL,
            block_reason = NULL,
            spam_strikes = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE vk_id = ?;
        """,
        (vk_id,),
    )


async def is_user_blocked(vk_id: int) -> tuple[bool, str | None, str | None]:
    row = await get_user_by_vk_id(vk_id)
    if not row:
        return False, None, None

    is_blocked = bool(row.get("is_blocked", 0))
    blocked_until = row.get("blocked_until")
    reason = row.get("block_reason")

    if not is_blocked:
        return False, None, None

    if blocked_until:
        try:
            until = datetime.fromisoformat(str(blocked_until))
            if until <= datetime.now():
                await set_user_block(vk_id, False)
                return False, None, None
        except ValueError:
            pass

    return True, str(reason) if reason else None, str(blocked_until) if blocked_until else None
