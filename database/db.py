from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiosqlite

from utils.content_defaults import DEFAULT_CONTENT

logger = logging.getLogger(__name__)


DEMO_TOURS: list[dict[str, Any]] = [
    {
        "name": "Турция All Inclusive Antalya",
        "country": "Турция",
        "destination": "Анталья",
        "travel_scope": "abroad",
        "price_per_person": 79000,
        "duration_days": 7,
        "rest_type": "пляжный",
        "available_from": "2026-04-01",
        "available_to": "2026-11-15",
        "description": "Анталья, отель 5*, первая линия и комфортный формат all inclusive.",
        "photo_url": "https://images.unsplash.com/photo-1526481280695-3c4691c8b4f0?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Турция Kemer Family",
        "country": "Турция",
        "destination": "Кемер",
        "travel_scope": "abroad",
        "price_per_person": 84500,
        "duration_days": 8,
        "rest_type": "семейный",
        "available_from": "2026-04-15",
        "available_to": "2026-10-31",
        "description": "Семейный отель с анимацией, бассейнами и удобным пляжем.",
        "photo_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Турция Cappadocia Discovery",
        "country": "Турция",
        "destination": "Каппадокия",
        "travel_scope": "abroad",
        "price_per_person": 98000,
        "duration_days": 6,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-20",
        "available_to": "2026-11-10",
        "description": "Стамбул и Каппадокия с насыщенной экскурсионной программой.",
        "photo_url": "https://images.unsplash.com/photo-1641412281936-df5d4d0f5f5f?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Египет Hurghada Red Sea",
        "country": "Египет",
        "destination": "Хургада",
        "travel_scope": "abroad",
        "price_per_person": 76000,
        "duration_days": 7,
        "rest_type": "пляжный",
        "available_from": "2026-03-15",
        "available_to": "2026-12-20",
        "description": "Песчаный пляж, коралловые рифы и удобный формат отдыха у моря.",
        "photo_url": "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Египет Sharm Snorkeling",
        "country": "Египет",
        "destination": "Шарм-эль-Шейх",
        "travel_scope": "abroad",
        "price_per_person": 89000,
        "duration_days": 8,
        "rest_type": "активный",
        "available_from": "2026-03-15",
        "available_to": "2026-12-20",
        "description": "Дайвинг, снорклинг и активный формат отдыха на Красном море.",
        "photo_url": "https://images.unsplash.com/photo-1589197331516-4ddf6d4b2d0a?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "ОАЭ Dubai City Escape",
        "country": "ОАЭ",
        "destination": "Дубай",
        "travel_scope": "abroad",
        "price_per_person": 105000,
        "duration_days": 6,
        "rest_type": "экскурсионный",
        "available_from": "2026-01-10",
        "available_to": "2026-12-31",
        "description": "Дубай, высокий сервис, шопинг и экскурсии по городу.",
        "photo_url": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "ОАЭ Ras Al Khaimah Beach",
        "country": "ОАЭ",
        "destination": "Рас-эль-Хайма",
        "travel_scope": "abroad",
        "price_per_person": 112000,
        "duration_days": 7,
        "rest_type": "пляжный",
        "available_from": "2026-01-10",
        "available_to": "2026-12-31",
        "description": "Спокойный пляжный отдых с хорошим уровнем сервиса.",
        "photo_url": "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Таиланд Phuket Relax",
        "country": "Таиланд",
        "destination": "Пхукет",
        "travel_scope": "abroad",
        "price_per_person": 124000,
        "duration_days": 10,
        "rest_type": "пляжный",
        "available_from": "2026-10-01",
        "available_to": "2027-04-20",
        "description": "Теплое море, тропики и удобный зимний формат пляжного отдыха.",
        "photo_url": "https://images.unsplash.com/photo-1468413253725-0d5181091126?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Таиланд Pattaya Weekend Plus",
        "country": "Таиланд",
        "destination": "Паттайя",
        "travel_scope": "abroad",
        "price_per_person": 109000,
        "duration_days": 8,
        "rest_type": "экскурсионный",
        "available_from": "2026-10-01",
        "available_to": "2027-04-20",
        "description": "Паттайя с экскурсиями и активным досугом в сочетании с пляжем.",
        "photo_url": "https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Вьетнам Nha Trang Coast",
        "country": "Вьетнам",
        "destination": "Нячанг",
        "travel_scope": "abroad",
        "price_per_person": 118000,
        "duration_days": 9,
        "rest_type": "пляжный",
        "available_from": "2026-11-01",
        "available_to": "2027-04-30",
        "description": "Пляжный отдых с мягким климатом и хорошим городским сервисом.",
        "photo_url": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Шри-Ланка Ocean Escape",
        "country": "Шри-Ланка",
        "destination": "Бентота",
        "travel_scope": "abroad",
        "price_per_person": 133000,
        "duration_days": 9,
        "rest_type": "пляжный",
        "available_from": "2026-11-01",
        "available_to": "2027-04-30",
        "description": "Океан, тропическая природа и спокойный отдых у воды.",
        "photo_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Мальдивы Premium Lagoon",
        "country": "Мальдивы",
        "destination": "Мале Атолл",
        "travel_scope": "abroad",
        "price_per_person": 245000,
        "duration_days": 7,
        "rest_type": "оздоровительный",
        "available_from": "2026-01-15",
        "available_to": "2026-12-31",
        "description": "Премиальный островной отдых, уединение и красивые лагуны.",
        "photo_url": "https://images.unsplash.com/photo-1573843981267-be1999ff37cd?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Китай Hainan Beach",
        "country": "Китай",
        "destination": "Хайнань",
        "travel_scope": "abroad",
        "price_per_person": 136000,
        "duration_days": 9,
        "rest_type": "пляжный",
        "available_from": "2026-10-01",
        "available_to": "2027-04-30",
        "description": "Теплое море, пляжный отдых и комфортный перелет из России.",
        "photo_url": "https://images.unsplash.com/photo-1549692520-acc6669e2f0c?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Китай Beijing & Shanghai",
        "country": "Китай",
        "destination": "Пекин и Шанхай",
        "travel_scope": "abroad",
        "price_per_person": 128000,
        "duration_days": 7,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-11-30",
        "description": "Крупные города Китая с насыщенной экскурсионной программой.",
        "photo_url": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Абхазия Гагра Family",
        "country": "Абхазия",
        "destination": "Гагра",
        "travel_scope": "abroad",
        "price_per_person": 52000,
        "duration_days": 8,
        "rest_type": "семейный",
        "available_from": "2026-05-01",
        "available_to": "2026-10-10",
        "description": "Бюджетный семейный отдых у моря без сложной логистики.",
        "photo_url": "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Беларусь Minsk Wellness",
        "country": "Беларусь",
        "destination": "Минск",
        "travel_scope": "abroad",
        "price_per_person": 46000,
        "duration_days": 5,
        "rest_type": "оздоровительный",
        "available_from": "2026-01-15",
        "available_to": "2026-12-20",
        "description": "Санаторный и городской формат отдыха с короткой логистикой.",
        "photo_url": "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Грузия Tbilisi & Mountains",
        "country": "Грузия",
        "destination": "Тбилиси",
        "travel_scope": "abroad",
        "price_per_person": 68000,
        "duration_days": 6,
        "rest_type": "экскурсионный",
        "available_from": "2026-04-01",
        "available_to": "2026-11-20",
        "description": "Тбилиси, гастрономия и атмосферные горные маршруты.",
        "photo_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Армения Yerevan Discovery",
        "country": "Армения",
        "destination": "Ереван",
        "travel_scope": "abroad",
        "price_per_person": 61000,
        "duration_days": 5,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-11-30",
        "description": "Ереван, Севан и Дилижан в коротком экскурсионном туре.",
        "photo_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Узбекистан Silk Road",
        "country": "Узбекистан",
        "destination": "Самарканд",
        "travel_scope": "abroad",
        "price_per_person": 74000,
        "duration_days": 6,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-11-30",
        "description": "Маршрут по городам Шелкового пути с восточной архитектурой.",
        "photo_url": "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Сочи Family",
        "country": "Россия",
        "destination": "Сочи",
        "travel_scope": "domestic",
        "price_per_person": 52000,
        "duration_days": 8,
        "rest_type": "семейный",
        "available_from": "2026-05-01",
        "available_to": "2026-10-15",
        "description": "Сочи, семейный отель с анимацией, морем и удобным трансфером.",
        "photo_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Адлер Seaside",
        "country": "Россия",
        "destination": "Адлер",
        "travel_scope": "domestic",
        "price_per_person": 49500,
        "duration_days": 7,
        "rest_type": "пляжный",
        "available_from": "2026-05-01",
        "available_to": "2026-10-10",
        "description": "Адлер для легкого пляжного отдыха с коротким перелетом.",
        "photo_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Красная Поляна Weekend",
        "country": "Россия",
        "destination": "Красная Поляна",
        "travel_scope": "domestic",
        "price_per_person": 58000,
        "duration_days": 5,
        "rest_type": "активный",
        "available_from": "2026-04-01",
        "available_to": "2026-11-20",
        "description": "Горы, прогулки, канатные дороги и активный формат отдыха.",
        "photo_url": "https://images.unsplash.com/photo-1500534314209-a26db0f5b1ef?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Калининград City Break",
        "country": "Россия",
        "destination": "Калининград",
        "travel_scope": "domestic",
        "price_per_person": 47000,
        "duration_days": 5,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-12-20",
        "description": "Калининград и Светлогорск для короткого культурного отдыха.",
        "photo_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Санкт-Петербург Classic",
        "country": "Россия",
        "destination": "Санкт-Петербург",
        "travel_scope": "domestic",
        "price_per_person": 43000,
        "duration_days": 4,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-12-25",
        "description": "Эрмитаж, каналы и насыщенный городской уикенд.",
        "photo_url": "https://images.unsplash.com/photo-1513326738677-b964603b136d?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Казань Discovery",
        "country": "Россия",
        "destination": "Казань",
        "travel_scope": "domestic",
        "price_per_person": 39000,
        "duration_days": 4,
        "rest_type": "экскурсионный",
        "available_from": "2026-03-01",
        "available_to": "2026-12-25",
        "description": "Казань с гастрономией, центром города и историческими маршрутами.",
        "photo_url": "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Байкал Active",
        "country": "Россия",
        "destination": "Байкал",
        "travel_scope": "domestic",
        "price_per_person": 69000,
        "duration_days": 7,
        "rest_type": "активный",
        "available_from": "2026-06-01",
        "available_to": "2026-09-20",
        "description": "Трекинг, прогулки на катере и эко-формат отдыха на Байкале.",
        "photo_url": "https://images.unsplash.com/photo-1482192596544-9eb780fc7f66?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Алтай Adventure",
        "country": "Россия",
        "destination": "Алтай",
        "travel_scope": "domestic",
        "price_per_person": 72000,
        "duration_days": 7,
        "rest_type": "активный",
        "available_from": "2026-05-20",
        "available_to": "2026-09-25",
        "description": "Горы, реки, джип-туры и активный формат отдыха на Алтае.",
        "photo_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Карелия Nature",
        "country": "Россия",
        "destination": "Карелия",
        "travel_scope": "domestic",
        "price_per_person": 49000,
        "duration_days": 5,
        "rest_type": "оздоровительный",
        "available_from": "2026-05-01",
        "available_to": "2026-09-30",
        "description": "Озера, леса и спокойный отдых на природе с банным комплексом.",
        "photo_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Домбай Mountain Escape",
        "country": "Россия",
        "destination": "Домбай",
        "travel_scope": "domestic",
        "price_per_person": 56000,
        "duration_days": 6,
        "rest_type": "активный",
        "available_from": "2026-05-01",
        "available_to": "2026-10-15",
        "description": "Горные виды, прогулки и активный отдых на Кавказе.",
        "photo_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Шерегеш Ski",
        "country": "Россия",
        "destination": "Шерегеш",
        "travel_scope": "domestic",
        "price_per_person": 61000,
        "duration_days": 6,
        "rest_type": "горнолыжный",
        "available_from": "2026-11-20",
        "available_to": "2027-03-30",
        "description": "Перелет, трансфер и ski-pass для горнолыжного отдыха.",
        "photo_url": "https://images.unsplash.com/photo-1510798831971-661eb04b3739?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Кавказские Минеральные Воды",
        "country": "Россия",
        "destination": "Кавказские Минеральные Воды",
        "travel_scope": "domestic",
        "price_per_person": 58000,
        "duration_days": 7,
        "rest_type": "оздоровительный",
        "available_from": "2026-02-01",
        "available_to": "2026-12-20",
        "description": "Санаторный отдых и восстановление в Кисловодске и Ессентуках.",
        "photo_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Россия Владивосток Pacific",
        "country": "Россия",
        "destination": "Владивосток",
        "travel_scope": "domestic",
        "price_per_person": 67000,
        "duration_days": 6,
        "rest_type": "экскурсионный",
        "available_from": "2026-05-01",
        "available_to": "2026-10-10",
        "description": "Приморье, бухты и городской отдых на берегу Тихого океана.",
        "photo_url": "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1200&q=80",
    },
]

LEGACY_DISABLED_TOURS = {"Италия Weekend"}


class Database:
    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self, db_path: str) -> None:
        self._conn = await aiosqlite.connect(db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def init_schema(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER UNIQUE NOT NULL,
                full_name TEXT,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_manager INTEGER NOT NULL DEFAULT 0,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                blocked_until TEXT,
                block_reason TEXT,
                spam_strikes INTEGER NOT NULL DEFAULT 0,
                last_assigned_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                travel_scope TEXT,
                country TEXT,
                destination TEXT,
                budget INTEGER,
                travelers INTEGER,
                start_date TEXT,
                end_date TEXT,
                rest_type TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                manager_required INTEGER NOT NULL DEFAULT 0,
                assigned_manager_vk_id INTEGER,
                sla_15_sent INTEGER NOT NULL DEFAULT 0,
                sla_30_sent INTEGER NOT NULL DEFAULT 0,
                sla_60_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                destination TEXT,
                travel_scope TEXT NOT NULL DEFAULT 'abroad',
                price_per_person INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                rest_type TEXT NOT NULL,
                available_from TEXT,
                available_to TEXT,
                description TEXT,
                photo_url TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                message TEXT,
                level TEXT NOT NULL DEFAULT 'INFO',
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS content_blocks (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_favorite_tours (
                user_id INTEGER NOT NULL,
                tour_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, tour_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(tour_id) REFERENCES tours(id) ON DELETE CASCADE
            );
            """,
        ]

        async with self._lock:
            for query in queries:
                await self._conn.execute(query)
            await self._ensure_user_columns()
            await self._ensure_request_columns()
            await self._ensure_tour_columns()
            await self._seed_content()
            await self._conn.commit()

        await self._seed_tours()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        async with self._lock:
            cursor = await self._conn.execute(query, params)
            await self._conn.commit()
            return cursor.lastrowid

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        async with self._lock:
            cursor = await self._conn.execute(query, params)
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = await self.fetchall(query, params)
        return rows[0] if rows else None

    async def _table_columns(self, table_name: str) -> set[str]:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        cursor = await self._conn.execute(f"PRAGMA table_info({table_name});")
        rows = await cursor.fetchall()
        return {str(row[1]) for row in rows}

    async def _ensure_request_columns(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        columns = await self._table_columns("requests")
        if "travel_scope" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN travel_scope TEXT;")
        if "destination" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN destination TEXT;")
        if "updated_at" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN updated_at TEXT;")
            await self._conn.execute(
                "UPDATE requests SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP);"
            )
        if "assigned_manager_vk_id" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN assigned_manager_vk_id INTEGER;")
        if "sla_15_sent" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN sla_15_sent INTEGER NOT NULL DEFAULT 0;")
        if "sla_30_sent" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN sla_30_sent INTEGER NOT NULL DEFAULT 0;")
        if "sla_60_sent" not in columns:
            await self._conn.execute("ALTER TABLE requests ADD COLUMN sla_60_sent INTEGER NOT NULL DEFAULT 0;")

    async def _ensure_user_columns(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        columns = await self._table_columns("users")
        if "is_manager" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN is_manager INTEGER NOT NULL DEFAULT 0;")
        if "is_blocked" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0;")
        if "blocked_until" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN blocked_until TEXT;")
        if "block_reason" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN block_reason TEXT;")
        if "spam_strikes" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN spam_strikes INTEGER NOT NULL DEFAULT 0;")
        if "last_assigned_at" not in columns:
            await self._conn.execute("ALTER TABLE users ADD COLUMN last_assigned_at TEXT;")

    async def _ensure_tour_columns(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        columns = await self._table_columns("tours")
        if "destination" not in columns:
            await self._conn.execute("ALTER TABLE tours ADD COLUMN destination TEXT;")
        if "travel_scope" not in columns:
            await self._conn.execute("ALTER TABLE tours ADD COLUMN travel_scope TEXT DEFAULT 'abroad';")
        if "photo_url" not in columns:
            await self._conn.execute("ALTER TABLE tours ADD COLUMN photo_url TEXT;")

    async def _seed_content(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        for key, value in DEFAULT_CONTENT.items():
            await self._conn.execute(
                """
                INSERT INTO content_blocks (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO NOTHING;
                """,
                (key, value),
            )

    async def _seed_tours(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")

        logger.info("Ensuring demo tours are present")
        existing_rows = await self.fetchall("SELECT id, name FROM tours;")
        existing_names = {str(row["name"]) for row in existing_rows}

        insert_query = """
            INSERT INTO tours (
                name, country, destination, travel_scope, price_per_person, duration_days,
                rest_type, available_from, available_to, description, photo_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        to_insert = [
            (
                tour["name"],
                tour["country"],
                tour["destination"],
                tour["travel_scope"],
                tour["price_per_person"],
                tour["duration_days"],
                tour["rest_type"],
                tour["available_from"],
                tour["available_to"],
                tour["description"],
                tour["photo_url"],
            )
            for tour in DEMO_TOURS
            if tour["name"] not in existing_names
        ]

        async with self._lock:
            if LEGACY_DISABLED_TOURS:
                placeholders = ",".join("?" for _ in LEGACY_DISABLED_TOURS)
                await self._conn.execute(
                    f"UPDATE tours SET is_active = 0 WHERE name IN ({placeholders});",
                    tuple(LEGACY_DISABLED_TOURS),
                )

            for tour in DEMO_TOURS:
                await self._conn.execute(
                    """
                    UPDATE tours
                    SET country = ?,
                        destination = COALESCE(NULLIF(destination, ''), ?),
                        travel_scope = COALESCE(NULLIF(travel_scope, ''), ?),
                        description = COALESCE(NULLIF(description, ''), ?),
                        photo_url = COALESCE(NULLIF(photo_url, ''), ?)
                    WHERE name = ?;
                    """,
                    (
                        tour["country"],
                        tour["destination"],
                        tour["travel_scope"],
                        tour["description"],
                        tour["photo_url"],
                        tour["name"],
                    ),
                )

            await self._conn.execute(
                """
                UPDATE tours
                SET travel_scope = CASE
                    WHEN lower(country) = lower('Россия') THEN 'domestic'
                    ELSE COALESCE(NULLIF(travel_scope, ''), 'abroad')
                END;
                """
            )

            if to_insert:
                await self._conn.executemany(insert_query, to_insert)
            await self._conn.commit()


db = Database()
