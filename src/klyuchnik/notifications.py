from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from aiogram import Bot

from klyuchnik.locks.base import Lock


class LockNotifier(Protocol):
    async def notify_low_battery(self, *, lock: Lock, battery_percent: int | None) -> None: ...
    async def notify_rate_limit_exceeded(self, *, lock: Lock, user_id: int) -> None: ...
    async def notify_lock_opened(self, *, lock: Lock, user_id: int, user_name: str) -> None: ...


class NullLockNotifier:
    async def notify_low_battery(self, *, lock: Lock, battery_percent: int | None) -> None:
        return None

    async def notify_rate_limit_exceeded(self, *, lock: Lock, user_id: int) -> None:
        return None

    async def notify_lock_opened(self, *, lock: Lock, user_id: int, user_name: str) -> None:
        return None


class TelegramLockNotifier:
    def __init__(self, bot: Bot, chat_id: int, audit_chat_id: int | None = None) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._audit_chat_id = audit_chat_id

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

    async def notify_lock_opened(self, *, lock: Lock, user_id: int, user_name: str) -> None:
        if self._audit_chat_id is None:
            return
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        await self._bot.send_message(
            chat_id=self._audit_chat_id,
            text=f"[{ts}] {user_name} (id={user_id}) открыл «{lock.title}»",
            parse_mode=None,
        )
