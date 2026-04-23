from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

from klyuchnik.handlers.callbacks import handle_lock_open
from klyuchnik.keyboards import LockCallback
from klyuchnik.locks.base import LockResult
from klyuchnik.locks.registry import LockRegistry


@dataclass
class _StubLock:
    id: str
    title: str
    result: LockResult = field(default_factory=lambda: LockResult(True, "HTTP 200"))
    opened: int = 0

    async def open(self) -> LockResult:
        self.opened += 1
        return self.result


def _callback(lock_id: str, user_id: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        data=LockCallback(action="open", lock_id=lock_id).pack(),
        answer=AsyncMock(),
    )


async def test_member_opens_lock_successfully() -> None:
    lock = _StubLock("a", "A")
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    cb = _callback("a")

    await handle_lock_open(
        callback=cb,
        lock_id="a",
        registry=registry,
        membership=membership,
    )

    assert lock.opened == 1
    membership.is_member.assert_awaited_once_with(42)
    cb.answer.assert_awaited_once()
    text = cb.answer.call_args.args[0] if cb.answer.call_args.args else cb.answer.call_args.kwargs.get("text")
    assert text is not None


async def test_non_member_does_not_trigger_lock() -> None:
    lock = _StubLock("a", "A")
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=False))
    cb = _callback("a", user_id=77)

    await handle_lock_open(
        callback=cb,
        lock_id="a",
        registry=registry,
        membership=membership,
    )

    assert lock.opened == 0
    membership.is_member.assert_awaited_once_with(77)
    cb.answer.assert_awaited_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True


async def test_unknown_lock_id_answers_with_error_and_no_membership_check() -> None:
    registry = LockRegistry([_StubLock("a", "A")])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    cb = _callback("zzz")

    await handle_lock_open(
        callback=cb,
        lock_id="zzz",
        registry=registry,
        membership=membership,
    )

    membership.is_member.assert_not_awaited()
    cb.answer.assert_awaited_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True


async def test_failed_lock_is_reported_as_alert() -> None:
    lock = _StubLock("a", "A", result=LockResult(False, "HTTP 500"))
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    cb = _callback("a")

    await handle_lock_open(
        callback=cb,
        lock_id="a",
        registry=registry,
        membership=membership,
    )

    assert lock.opened == 1
    cb.answer.assert_awaited_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True
