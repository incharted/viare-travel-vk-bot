from __future__ import annotations

from config import get_settings
from services.users import get_user_by_vk_id


async def is_admin(vk_id: int) -> bool:
    settings = get_settings()
    if vk_id in settings.admin_ids:
        return True

    user = await get_user_by_vk_id(vk_id)
    if not user:
        return False
    return bool(user.get("is_admin", 0))


async def is_manager(vk_id: int) -> bool:
    settings = get_settings()
    if vk_id in settings.manager_ids:
        return True

    user = await get_user_by_vk_id(vk_id)
    if not user:
        return False
    return bool(user.get("is_manager", 0) or user.get("is_admin", 0))


async def is_staff(vk_id: int) -> bool:
    return await is_admin(vk_id) or await is_manager(vk_id)


async def get_staff_role(vk_id: int) -> str | None:
    if await is_admin(vk_id):
        return "admin"
    if await is_manager(vk_id):
        return "manager"
    return None
