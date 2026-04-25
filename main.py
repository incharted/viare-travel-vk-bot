from __future__ import annotations

import asyncio
import logging
import ssl

import certifi
from vkbottle import API, BuiltinStateDispenser
from vkbottle.bot import Bot, BotLabeler
from vkbottle.tools import LoopWrapper

from config import get_settings
from database.db import db
from handlers import register_all_handlers
from middlewares import AntiFraudMiddleware, AuditMiddleware, RateLimitMiddleware, TextNormalizeMiddleware
from services.sla import start_sla_worker
from utils.logger import configure_logging
from utils.single_instance import acquire_process_lock
from utils.vk_http_client import VkAiohttpClient

logger = logging.getLogger(__name__)


async def init_db(db_path: str) -> None:
    await db.connect(db_path)
    await db.init_schema()


def build_bot(loop: asyncio.AbstractEventLoop) -> Bot:
    settings = get_settings()
    if settings.vk_ssl_verify:
        ssl_context = ssl.create_default_context(cafile=settings.ca_bundle_path or certifi.where())
    else:
        logger.warning("VK_SSL_VERIFY is disabled. Use only for local troubleshooting.")
        ssl_context = False

    http_client = VkAiohttpClient(ssl_option=ssl_context)
    api = API(settings.vk_token, http_client=http_client)
    labeler = BotLabeler()
    built_bot = Bot(
        api=api,
        labeler=labeler,
        state_dispenser=BuiltinStateDispenser(),
        loop_wrapper=LoopWrapper(loop=loop),
    )

    # middleware chain for every incoming user message
    labeler.message_view.register_middleware(TextNormalizeMiddleware)
    labeler.message_view.register_middleware(AntiFraudMiddleware)
    labeler.message_view.register_middleware(RateLimitMiddleware)
    labeler.message_view.register_middleware(AuditMiddleware)

    register_all_handlers(labeler, built_bot)
    return built_bot


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_file)

    lock_handle = acquire_process_lock("./data/bot.lock")
    if lock_handle is None:
        logger.error("Another bot instance is already running. Stop the previous copy before starting a new one.")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(init_db(settings.db_path))
    bot = build_bot(loop)
    start_sla_worker(loop, bot)

    logger.info("Bot started in %s mode", settings.app_env)
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    finally:
        try:
            if not loop.is_closed():
                loop.run_until_complete(db.close())
        finally:
            lock_handle.close()
            if not loop.is_closed():
                loop.close()


if __name__ == "__main__":
    main()
