from __future__ import annotations

from datetime import datetime

from config import get_settings
from database.db import db
from services.requests import assign_request_manager, get_request_by_id
from services.users import touch_manager_assignment

ACTIVE_STATUSES = ("new", "in_progress", "waiting_client")


def _is_blocked_row(row: dict) -> bool:
    if int(row.get("is_blocked") or 0) == 0:
        return False

    blocked_until = row.get("blocked_until")
    if not blocked_until:
        return True

    try:
        until = datetime.fromisoformat(str(blocked_until))
    except ValueError:
        return True
    return until > datetime.now()


async def _manager_candidates() -> list[int]:
    settings = get_settings()
    candidates: set[int] = set(vk_id for vk_id in settings.manager_ids if vk_id not in settings.admin_ids)

    manager_rows = await db.fetchall(
        "SELECT vk_id, is_blocked, blocked_until FROM users WHERE is_manager = 1 AND is_admin = 0;"
    )
    candidates.update(
        int(row["vk_id"])
        for row in manager_rows
        if row.get("vk_id") and not _is_blocked_row(row)
    )
    if candidates:
        return sorted(candidates)

    fallback: set[int] = set(settings.manager_ids)
    fallback.update(settings.admin_ids)
    staff_rows = await db.fetchall(
        "SELECT vk_id, is_blocked, blocked_until FROM users WHERE is_manager = 1 OR is_admin = 1;"
    )
    fallback.update(
        int(row["vk_id"])
        for row in staff_rows
        if row.get("vk_id") and not _is_blocked_row(row)
    )
    return sorted(fallback)


async def _manager_active_load_map() -> dict[int, int]:
    placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
    rows = await db.fetchall(
        f"""
        SELECT assigned_manager_vk_id AS manager_vk_id, COUNT(*) AS c
        FROM requests
        WHERE assigned_manager_vk_id IS NOT NULL
          AND status IN ({placeholders})
        GROUP BY assigned_manager_vk_id;
        """,
        ACTIVE_STATUSES,
    )
    return {int(row["manager_vk_id"]): int(row["c"]) for row in rows if row.get("manager_vk_id")}


async def get_manager_load_calendar() -> dict:
    manager_ids = await _manager_candidates()
    if not manager_ids:
        return {"managers": [], "unassigned_active": 0}

    load_map = await _manager_active_load_map()
    manager_rows = await db.fetchall(
        """
        SELECT vk_id, last_assigned_at
        FROM users
        WHERE vk_id IN ({})
        ORDER BY vk_id ASC;
        """.format(",".join("?" for _ in manager_ids)),
        tuple(manager_ids),
    )
    last_assigned_map = {int(row["vk_id"]): row.get("last_assigned_at") for row in manager_rows if row.get("vk_id")}

    managers = [
        {
            "vk_id": vk_id,
            "active_requests": int(load_map.get(vk_id) or 0),
            "last_assigned_at": last_assigned_map.get(vk_id),
        }
        for vk_id in manager_ids
    ]
    managers.sort(key=lambda item: (item["active_requests"], item.get("last_assigned_at") or "", item["vk_id"]))

    unassigned_row = await db.fetchone(
        """
        SELECT COUNT(*) AS c
        FROM requests
        WHERE assigned_manager_vk_id IS NULL
          AND status IN ('new', 'in_progress', 'waiting_client');
        """
    )

    return {
        "managers": managers,
        "unassigned_active": int((unassigned_row or {}).get("c") or 0),
    }


async def choose_manager_for_request() -> int | None:
    calendar = await get_manager_load_calendar()
    managers = calendar.get("managers", [])
    if not managers:
        return None
    return int(managers[0]["vk_id"])


async def auto_assign_request(request_id: int) -> int | None:
    request = await get_request_by_id(request_id)
    if not request:
        return None
    assigned = request.get("assigned_manager_vk_id")
    if assigned:
        return int(assigned)

    manager_vk_id = await choose_manager_for_request()
    if not manager_vk_id:
        return None

    await assign_request_manager(request_id, manager_vk_id)
    await touch_manager_assignment(manager_vk_id)
    return manager_vk_id
