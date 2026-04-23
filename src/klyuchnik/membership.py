from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

_log = logging.getLogger(__name__)

_ACTIVE_STATUSES = frozenset({"creator", "administrator", "member"})


class MembershipChecker:
    """Wraps `bot.get_chat_member` with per-user TTL cache.

    Kept intentionally tiny: a positive result is cached for `ttl_s` seconds.
    Negative results and API errors are NOT cached, so a user who just joined
    is not locked out for a whole TTL window.
    """

    def __init__(
        self,
        bot: Bot | Any,
        chat_id: int,
        ttl_s: float = 60.0,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._ttl_s = ttl_s
        self._now = time_source
        self._cache: dict[int, float] = {}

    async def is_member(self, user_id: int) -> bool:
        expires_at = self._cache.get(user_id)
        if expires_at is not None and expires_at > self._now():
            return True

        try:
            member = await self._bot.get_chat_member(self._chat_id, user_id)
        except TelegramAPIError as exc:
            _log.warning("get_chat_member(%s, %s) failed: %s", self._chat_id, user_id, exc)
            return False

        if self._is_active(member):
            self._cache[user_id] = self._now() + self._ttl_s
            return True

        self._cache.pop(user_id, None)
        return False

    @staticmethod
    def _is_active(member: Any) -> bool:
        status = getattr(member, "status", None)
        if status in _ACTIVE_STATUSES:
            return True
        if status == "restricted":
            return bool(getattr(member, "is_member", False))
        return False
