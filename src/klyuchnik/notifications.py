from __future__ import annotations

from typing import Protocol

from aiogram import Bot

from klyuchnik.locks.base import Lock


class LockNotifier(Protocol):
    async def notify_low_battery(self, *, lock: Lock, battery_percent: int | None) -> None: ...
    async def notify_rate_limit_exceeded(self, *, lock: Lock, user_id: int) -> None: ...


class NullLockNotifier:
    async def notify_low_battery(self, *, lock: Lock, battery_percent: int | None) -> None:
        return None

    async def notify_rate_limit_exceeded(self, *, lock: Lock, user_id: int) -> None:
        return None


class TelegramLockNotifier:
    def __init__(self, bot: Bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def notify_low_battery(self, *, lock: Lock, battery_percent: int | None) -> None:
        percent = "неизвестно" if battery_percent is None else f"{battery_percent}%"
        await self._bot.send_message(
            chat_id=self._chat_id,
            text=f"Батарейка замка «{lock.title}» разряжена: {percent}",
            parse_mode=None,
        )

    async def notify_rate_limit_exceeded(self, *, lock: Lock, user_id: int) -> None:
        await self._bot.send_message(
            chat_id=self._chat_id,
            text=f"Пользователь {user_id} исчерпал дневной лимит открытий замка «{lock.title}»",
            parse_mode=None,
        )
