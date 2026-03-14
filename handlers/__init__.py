from vkbottle.bot import Bot, BotLabeler

from handlers.admin import register_admin_handlers
from handlers.common import register_common_handlers
from handlers.tour_selection import register_tour_handlers


def register_all_handlers(labeler: BotLabeler, bot: Bot) -> None:
    register_admin_handlers(labeler, bot)
    register_tour_handlers(labeler, bot)
    register_common_handlers(labeler, bot)
