from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str
    vk_token: str
    db_path: str
    log_level: str
    log_file: str
    rate_limit_count: int
    rate_limit_window_sec: int
    admin_ids: set[int]
    manager_ids: set[int]
    vk_ssl_verify: bool
    ca_bundle_path: str | None
    external_tours_enabled: bool
    travelata_base_url: str
    travelata_departure_city_id: int
    travelata_timeout_sec: int
    travelata_max_results: int


def _parse_ids(raw_value: str) -> set[int]:
    result: set[int] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    token = os.getenv("VK_TOKEN", "").strip()
    if not token:
        raise ValueError("VK_TOKEN is empty. Set it in .env")

    db_path = os.getenv("DB_PATH", "./data/bot.sqlite3").strip()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    admin_ids = _parse_ids(os.getenv("ADMIN_IDS", "").strip())
    manager_ids = _parse_ids(os.getenv("MANAGER_IDS", "").strip())
    manager_ids.update(admin_ids)

    default_log_level = "INFO" if app_env == "prod" else "DEBUG"

    return Settings(
        app_env=app_env,
        vk_token=token,
        db_path=db_path,
        log_level=os.getenv("LOG_LEVEL", default_log_level).upper(),
        log_file=os.getenv("LOG_FILE", "./data/bot.log"),
        rate_limit_count=int(os.getenv("RATE_LIMIT_COUNT", "8")),
        rate_limit_window_sec=int(os.getenv("RATE_LIMIT_WINDOW_SEC", "10")),
        admin_ids=admin_ids,
        manager_ids=manager_ids,
        vk_ssl_verify=os.getenv("VK_SSL_VERIFY", "1").strip() not in {"0", "false", "False"},
        ca_bundle_path=(os.getenv("CA_BUNDLE_PATH", "").strip() or None),
        external_tours_enabled=os.getenv("EXTERNAL_TOURS_ENABLED", "1").strip() not in {"0", "false", "False"},
        travelata_base_url=os.getenv("TRAVELATA_BASE_URL", "https://api-gateway.travelata.ru").strip(),
        travelata_departure_city_id=int(os.getenv("TRAVELATA_DEPARTURE_CITY_ID", "2")),
        travelata_timeout_sec=int(os.getenv("TRAVELATA_TIMEOUT_SEC", "12")),
        travelata_max_results=int(os.getenv("TRAVELATA_MAX_RESULTS", "5")),
    )
