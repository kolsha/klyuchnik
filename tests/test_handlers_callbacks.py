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


async def test_successful_open_records_rate_limit_success() -> None:
    lock = _StubLock("b", "B")
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    rate_limiter = SimpleNamespace(
        check=AsyncMock(return_value=SimpleNamespace(allowed=True)),
        record_success=AsyncMock(),
    )
    cb = _callback("b", user_id=42)

    await handle_lock_open(
        callback=cb,
        lock_id="b",
        registry=registry,
        membership=membership,
        rate_limiter=rate_limiter,
    )

    rate_limiter.check.assert_awaited_once_with(lock_id="b", user_id=42)
    rate_limiter.record_success.assert_awaited_once_with(lock_id="b", user_id=42)


async def test_failed_open_does_not_record_rate_limit_success() -> None:
    lock = _StubLock("b", "B", result=LockResult(False, "HTTP 500"))
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    rate_limiter = SimpleNamespace(
        check=AsyncMock(return_value=SimpleNamespace(allowed=True)),
        record_success=AsyncMock(),
    )
    cb = _callback("b")

    await handle_lock_open(
        callback=cb,
        lock_id="b",
        registry=registry,
        membership=membership,
        rate_limiter=rate_limiter,
    )

    rate_limiter.record_success.assert_not_awaited()


async def test_rate_limit_exceeded_does_not_trigger_lock_and_notifies_chat() -> None:
    lock = _StubLock("b", "B")
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    rate_limiter = SimpleNamespace(
        check=AsyncMock(return_value=SimpleNamespace(allowed=False)),
        record_success=AsyncMock(),
    )
    notifier = SimpleNamespace(
        notify_rate_limit_exceeded=AsyncMock(),
        notify_low_battery=AsyncMock(),
    )
    cb = _callback("b", user_id=42)

    await handle_lock_open(
        callback=cb,
        lock_id="b",
        registry=registry,
        membership=membership,
        rate_limiter=rate_limiter,
        notifier=notifier,
    )

    assert lock.opened == 0
    rate_limiter.record_success.assert_not_awaited()
    notifier.notify_rate_limit_exceeded.assert_awaited_once_with(lock=lock, user_id=42)
    cb.answer.assert_awaited_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True


async def test_low_battery_success_notifies_chat() -> None:
    lock = _StubLock(
        "b",
        "B",
        result=LockResult(True, "unlocking", battery_percent=20, is_low_battery=True),
    )
    registry = LockRegistry([lock])
    membership = SimpleNamespace(is_member=AsyncMock(return_value=True))
    notifier = SimpleNamespace(
        notify_rate_limit_exceeded=AsyncMock(),
        notify_low_battery=AsyncMock(),
    )
    cb = _callback("b")

    await handle_lock_open(
        callback=cb,
        lock_id="b",
        registry=registry,
        membership=membership,
        notifier=notifier,
    )

    notifier.notify_low_battery.assert_awaited_once_with(
        lock=lock,
        battery_percent=20,
    )


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
