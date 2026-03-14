from __future__ import annotations

import mimetypes
import random
from pathlib import Path

import aiohttp
from vkbottle.bot import Bot, Message

from config import get_settings
from utils.formatting import format_tour_card

VK_API_VERSION = "5.199"


async def _vk_method(method: str, params: dict[str, str | int]) -> dict:
    settings = get_settings()
    payload: dict[str, str | int] = {
        "access_token": settings.vk_token,
        "v": VK_API_VERSION,
    }
    payload.update(params)

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(f"https://api.vk.com/method/{method}", data=payload) as response:
            data = await response.json()
            if "error" in data:
                raise RuntimeError(str(data["error"]))
            return data["response"]


async def upload_photo_from_url(photo_url: str, peer_id: int) -> str | None:
    if not photo_url:
        return None

    normalized_url = photo_url if not photo_url.startswith("//") else f"https:{photo_url}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
        async with session.get(normalized_url) as response:
            if response.status != 200:
                return None
            content = await response.read()
            content_type = response.headers.get("Content-Type", "image/jpeg")

        upload_server = await _vk_method("photos.getMessagesUploadServer", {"peer_id": peer_id})
        form = aiohttp.FormData()
        form.add_field("photo", content, filename="tour.jpg", content_type=content_type)
        async with session.post(upload_server["upload_url"], data=form) as upload_response:
            upload_payload = await upload_response.json(content_type=None)

    save_response = await _vk_method(
        "photos.saveMessagesPhoto",
        {
            "photo": upload_payload["photo"],
            "server": upload_payload["server"],
            "hash": upload_payload["hash"],
        },
    )
    if not save_response:
        return None

    photo = save_response[0]
    return f"photo{photo['owner_id']}_{photo['id']}"


async def upload_document(file_path: Path, title: str) -> str | None:
    upload_server = await _vk_method("docs.getMessagesUploadServer", {"type": "doc"})
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
        form = aiohttp.FormData()
        form.add_field(
            "file",
            file_path.read_bytes(),
            filename=file_path.name,
            content_type=mime,
        )
        async with session.post(upload_server["upload_url"], data=form) as response:
            upload_payload = await response.json(content_type=None)

    save_response = await _vk_method("docs.save", {"file": upload_payload["file"], "title": title})
    doc = save_response["doc"]
    return f"doc{doc['owner_id']}_{doc['id']}"


async def send_tour_message(bot: Bot, message: Message, tour: dict, travelers: int) -> None:
    attachment = None
    photo_url = str(tour.get("photo_url") or "").strip()
    if photo_url:
        try:
            attachment = await upload_photo_from_url(photo_url, message.peer_id)
        except Exception:
            attachment = None

    await bot.api.messages.send(
        peer_id=message.peer_id,
        message=format_tour_card(tour, travelers),
        attachment=attachment,
        random_id=random.randint(1, 2_000_000_000),
    )
