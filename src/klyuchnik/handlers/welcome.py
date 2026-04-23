from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import Message

from klyuchnik.content import WelcomeContent
from klyuchnik.keyboards import build_locks_keyboard
from klyuchnik.locks.registry import LockRegistry
from klyuchnik.state import PinStateStore

_log = logging.getLogger(__name__)


async def send_welcome_message(
    *,
    bot: Bot | Any,
    chat_id: int,
    content: WelcomeContent,
    registry: LockRegistry,
    state: PinStateStore,
) -> int:
    """Post the welcome message with lock buttons and re-pin it.

    Order: send → unpin old → pin new → save id. If any step after `send`
    fails we still try to keep the state file consistent with what's in chat.
    """
    if content.photo_paths:
        await bot.send_media_group(chat_id=chat_id, media=content.as_media_group())

    text = "Выберите замок:" if (content.caption_fits and content.photo_paths) else content.text
    keyboard = build_locks_keyboard(registry)
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    new_id = int(sent.message_id)

    old_id = await state.load(chat_id)
    if old_id is not None and old_id != new_id:
        try:
            await bot.unpin_chat_message(chat_id=chat_id, message_id=old_id)
        except TelegramAPIError as exc:
            _log.info("Failed to unpin old message %s in %s: %s", old_id, chat_id, exc)

    try:
        await bot.pin_chat_message(
            chat_id=chat_id, message_id=new_id, disable_notification=True
        )
    except TelegramAPIError as exc:
        _log.warning("Failed to pin new message %s in %s: %s", new_id, chat_id, exc)

    await state.save(chat_id, new_id)
    return new_id


def build_welcome_router(
    chat_id: int,
    content: WelcomeContent,
    registry: LockRegistry,
    state: PinStateStore,
) -> Router:
    """Aiogram router: triggers on /start and when new members join the configured chat."""

    router = Router(name="welcome")

    @router.message(CommandStart(), F.chat.id == chat_id)
    async def _on_start(message: Message, bot: Bot) -> None:
        await send_welcome_message(
            bot=bot, chat_id=chat_id, content=content, registry=registry, state=state
        )

    @router.message(F.new_chat_members, F.chat.id == chat_id)
    async def _on_new_members(message: Message, bot: Bot) -> None:
        bot_user = await bot.me()
        human_members = [u for u in (message.new_chat_members or []) if u.id != bot_user.id]
        if not human_members:
            return
        await send_welcome_message(
            bot=bot, chat_id=chat_id, content=content, registry=registry, state=state
        )

    return router
