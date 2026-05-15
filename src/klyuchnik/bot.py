from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from klyuchnik.config import Settings
from klyuchnik.content import load_welcome_content
from klyuchnik.handlers.callbacks import build_callback_router
from klyuchnik.handlers.welcome import build_welcome_router
from klyuchnik.locks.http_lock import HttpLock
from klyuchnik.locks.registry import LockRegistry
from klyuchnik.locks.switchbot import SwitchbotLock
from klyuchnik.membership import MembershipChecker
from klyuchnik.notifications import TelegramLockNotifier
from klyuchnik.rate_limit import JsonDailyRateLimiter
from klyuchnik.state import JsonPinStateStore

_log = logging.getLogger(__name__)


def build_bot_and_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.app.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )

    registry = LockRegistry(
        [
            HttpLock(settings.lock_a.to_http_config()),
            SwitchbotLock(settings.lock_b.to_switchbot_config()),
        ]
    )

    content = load_welcome_content(
        markdown_path=settings.app.content_dir / "welcome.md",
        photos_dir=settings.app.content_dir / "photos",
    )

    state = JsonPinStateStore(settings.app.state_file)
    membership = MembershipChecker(
        bot, chat_id=settings.app.chat_id, ttl_s=settings.app.membership_ttl_s
    )
    rate_limiter = JsonDailyRateLimiter(
        path=settings.app.rate_limit_file,
        limits={settings.lock_b.id: settings.lock_b.rate_limit_daily_open_limit},
        retention_days=settings.app.rate_limit_retention_days,
    )
    notifier = TelegramLockNotifier(bot, chat_id=settings.app.chat_id)

    dp = Dispatcher()
    dp.include_router(
        build_welcome_router(
            chat_id=settings.app.chat_id,
            content=content,
            registry=registry,
            state=state,
        )
    )
    dp.include_router(
        build_callback_router(
            registry=registry,
            membership=membership,
            rate_limiter=rate_limiter,
            notifier=notifier,
        )
    )

    return bot, dp


async def run(settings: Settings) -> None:
    bot, dp = build_bot_and_dispatcher(settings)
    me = await bot.me()
    _log.info("Starting bot @%s for chat %s", me.username, settings.app.chat_id)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
