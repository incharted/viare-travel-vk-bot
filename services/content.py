from __future__ import annotations

from database.db import db
from utils.content_defaults import DEFAULT_CONTENT


async def get_content_block(key: str) -> str:
    row = await db.fetchone("SELECT value FROM content_blocks WHERE key = ?;", (key,))
    if row and row.get("value"):
        return str(row["value"])
    return DEFAULT_CONTENT.get(key, "")


async def update_content_block(key: str, value: str) -> None:
    await db.execute(
        """
        INSERT INTO content_blocks (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP;
        """,
        (key, value),
    )


async def list_content_blocks() -> list[dict]:
    return await db.fetchall(
        """
        SELECT key, value, updated_at
        FROM content_blocks
        ORDER BY key ASC;
        """
    )
