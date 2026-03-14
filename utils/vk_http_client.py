from __future__ import annotations

import ssl
from typing import Any

from vkbottle.http.aiohttp import AiohttpClient


class VkAiohttpClient(AiohttpClient):
    """Aiohttp client wrapper with default SSL mode for all VK API requests."""

    def __init__(self, ssl_option: ssl.SSLContext | bool) -> None:
        super().__init__()
        self._ssl_option = ssl_option

    async def request_raw(
        self,
        url: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        kwargs.setdefault("ssl", self._ssl_option)
        return await super().request_raw(url, method, data, **kwargs)
