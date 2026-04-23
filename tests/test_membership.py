from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from klyuchnik.membership import MembershipChecker


def _member(status: str, is_member: bool = True) -> SimpleNamespace:
    return SimpleNamespace(status=status, is_member=is_member)


@pytest.mark.parametrize("status", ["creator", "administrator", "member"])
async def test_active_statuses_are_members(status: str) -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=_member(status)))
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    assert await checker.is_member(42) is True


async def test_restricted_with_is_member_true_is_member() -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(return_value=_member("restricted", is_member=True))
    )
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    assert await checker.is_member(42) is True


async def test_restricted_with_is_member_false_is_not_member() -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(return_value=_member("restricted", is_member=False))
    )
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    assert await checker.is_member(42) is False


@pytest.mark.parametrize("status", ["left", "kicked"])
async def test_inactive_statuses_are_not_members(status: str) -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=_member(status)))
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    assert await checker.is_member(42) is False


async def test_result_is_cached_within_ttl() -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=_member("member")))
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    await checker.is_member(42)
    await checker.is_member(42)
    await checker.is_member(42)
    assert bot.get_chat_member.await_count == 1


async def test_cache_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=_member("member")))
    current = [1000.0]
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=30, time_source=lambda: current[0])
    await checker.is_member(42)
    current[0] += 31
    await checker.is_member(42)
    assert bot.get_chat_member.await_count == 2


async def test_api_error_returns_false_and_is_not_cached() -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(
            side_effect=TelegramBadRequest(method=None, message="user not found")
        )
    )
    checker = MembershipChecker(bot, chat_id=-1001, ttl_s=60)
    assert await checker.is_member(42) is False
    assert await checker.is_member(42) is False
    # Two calls since errors aren't cached
    assert bot.get_chat_member.await_count == 2
