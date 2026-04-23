from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramBadRequest

from klyuchnik.content import WelcomeContent
from klyuchnik.handlers.welcome import send_welcome_message
from klyuchnik.locks.base import LockResult
from klyuchnik.locks.registry import LockRegistry
from klyuchnik.state import JsonPinStateStore


@dataclass
class _FakeLock:
    id: str
    title: str

    async def open(self) -> LockResult:
        return LockResult(True, "")


def _make_bot() -> SimpleNamespace:
    return SimpleNamespace(
        send_media_group=AsyncMock(
            return_value=[SimpleNamespace(message_id=100), SimpleNamespace(message_id=101)]
        ),
        send_message=AsyncMock(return_value=SimpleNamespace(message_id=200)),
        pin_chat_message=AsyncMock(return_value=True),
        unpin_chat_message=AsyncMock(return_value=True),
    )


def _registry() -> LockRegistry:
    return LockRegistry([_FakeLock("a", "Open A"), _FakeLock("b", "Open B")])


async def test_send_welcome_with_photos_and_fitting_caption(tmp_path: Path) -> None:
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"x")
    content = WelcomeContent(text="Short", photo_paths=[photo])
    bot = _make_bot()
    store = JsonPinStateStore(tmp_path / "state.json")

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    bot.send_media_group.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    args, kwargs = bot.send_message.call_args
    assert kwargs.get("chat_id", args[0] if args else None) == -1001
    assert kwargs.get("reply_markup") is not None
    bot.pin_chat_message.assert_awaited_once_with(
        chat_id=-1001, message_id=200, disable_notification=True
    )
    bot.unpin_chat_message.assert_not_awaited()
    assert await store.load(-1001) == 200


async def test_send_welcome_without_photos(tmp_path: Path) -> None:
    content = WelcomeContent(text="Just text", photo_paths=[])
    bot = _make_bot()
    store = JsonPinStateStore(tmp_path / "state.json")

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    bot.send_media_group.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    bot.pin_chat_message.assert_awaited_once_with(
        chat_id=-1001, message_id=200, disable_notification=True
    )
    assert await store.load(-1001) == 200


async def test_send_welcome_unpins_previous_message(tmp_path: Path) -> None:
    content = WelcomeContent(text="hi", photo_paths=[])
    bot = _make_bot()
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 42)

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    bot.unpin_chat_message.assert_awaited_once_with(chat_id=-1001, message_id=42)
    bot.pin_chat_message.assert_awaited_once_with(
        chat_id=-1001, message_id=200, disable_notification=True
    )
    assert await store.load(-1001) == 200


async def test_send_welcome_order_is_send_then_unpin_then_pin_then_save(tmp_path: Path) -> None:
    content = WelcomeContent(text="hi", photo_paths=[])
    bot = _make_bot()
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 42)

    events: list[str] = []

    async def _send(*_a: object, **_kw: object) -> SimpleNamespace:
        events.append("send")
        return SimpleNamespace(message_id=200)

    async def _unpin(*_a: object, **_kw: object) -> bool:
        events.append("unpin")
        return True

    async def _pin(*_a: object, **_kw: object) -> bool:
        events.append("pin")
        return True

    bot.send_message.side_effect = _send
    bot.unpin_chat_message.side_effect = _unpin
    bot.pin_chat_message.side_effect = _pin

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    assert events == ["send", "unpin", "pin"]


async def test_send_welcome_swallows_unpin_errors(tmp_path: Path) -> None:
    content = WelcomeContent(text="hi", photo_paths=[])
    bot = _make_bot()
    bot.unpin_chat_message.side_effect = TelegramBadRequest(
        method=None, message="message to unpin not found"
    )
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 42)

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    bot.pin_chat_message.assert_awaited_once()
    assert await store.load(-1001) == 200


async def test_send_welcome_caption_not_fitting_sends_text_with_buttons(tmp_path: Path) -> None:
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"x")
    long_text = "x" * 2000
    content = WelcomeContent(text=long_text, photo_paths=[photo])
    bot = _make_bot()
    store = JsonPinStateStore(tmp_path / "state.json")

    await send_welcome_message(
        bot=bot, chat_id=-1001, content=content, registry=_registry(), state=store
    )

    bot.send_media_group.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.call_args.kwargs.get("text")
    assert sent_text is not None
    assert long_text in sent_text
