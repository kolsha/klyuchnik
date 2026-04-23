from __future__ import annotations

from dataclasses import dataclass

import pytest
from aiogram.types import InlineKeyboardMarkup

from klyuchnik.keyboards import LockCallback, build_locks_keyboard
from klyuchnik.locks.base import Lock, LockResult
from klyuchnik.locks.registry import LockRegistry


@dataclass
class _FakeLock:
    id: str
    title: str

    async def open(self) -> LockResult:
        return LockResult(True, "ok")


def test_build_locks_keyboard_has_button_per_lock() -> None:
    registry = LockRegistry([_FakeLock("a", "Open A"), _FakeLock("b", "Open B")])
    markup = build_locks_keyboard(registry)

    assert isinstance(markup, InlineKeyboardMarkup)
    flat = [btn for row in markup.inline_keyboard for btn in row]
    assert [b.text for b in flat] == ["Open A", "Open B"]


def test_build_locks_keyboard_callback_data_matches_factory() -> None:
    registry = LockRegistry([_FakeLock("a", "A"), _FakeLock("b", "B")])
    markup = build_locks_keyboard(registry)
    flat = [btn for row in markup.inline_keyboard for btn in row]

    a = LockCallback.unpack(flat[0].callback_data)
    b = LockCallback.unpack(flat[1].callback_data)
    assert (a.action, a.lock_id) == ("open", "a")
    assert (b.action, b.lock_id) == ("open", "b")


def test_build_locks_keyboard_rejects_empty_registry() -> None:
    with pytest.raises(ValueError):
        build_locks_keyboard(LockRegistry([]))


def test_registry_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError):
        LockRegistry([_FakeLock("a", "A"), _FakeLock("a", "B")])


def test_registry_lookup_and_iteration() -> None:
    locks: list[Lock] = [_FakeLock("a", "A"), _FakeLock("b", "B")]
    registry = LockRegistry(locks)
    assert registry.get("a").id == "a"
    assert registry.get("missing") is None
    assert len(registry) == 2
    assert [lock.id for lock in registry] == ["a", "b"]
