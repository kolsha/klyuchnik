from __future__ import annotations

import pytest
from aioresponses import aioresponses

from klyuchnik.locks.base import Lock, LockResult
from klyuchnik.locks.http_lock import HttpLock, HttpLockConfig


def test_http_lock_implements_protocol() -> None:
    lock: Lock = HttpLock(
        HttpLockConfig(id="a", title="A", method="POST", url="https://x/open"),
    )
    assert lock.id == "a"
    assert lock.title == "A"


async def test_http_lock_open_success_post_json_body() -> None:
    cfg = HttpLockConfig(
        id="a",
        title="Open A",
        method="POST",
        url="https://lock-a.example/open",
        headers={"Authorization": "Bearer secret"},
        json_body={"cmd": "open"},
        success_status=200,
        timeout_s=5,
    )
    lock = HttpLock(cfg)

    with aioresponses() as m:
        m.post("https://lock-a.example/open", status=200, payload={"ok": True})
        result = await lock.open()

    assert isinstance(result, LockResult)
    assert result.ok is True
    assert "200" in result.detail


async def test_http_lock_open_failure_on_wrong_status() -> None:
    cfg = HttpLockConfig(
        id="b",
        title="Open B",
        method="GET",
        url="https://lock-b.example/relay?on=1",
        success_status=200,
    )
    lock = HttpLock(cfg)

    with aioresponses() as m:
        m.get("https://lock-b.example/relay?on=1", status=500, body="boom")
        result = await lock.open()

    assert result.ok is False
    assert "500" in result.detail


async def test_http_lock_open_timeout_returns_failure() -> None:
    cfg = HttpLockConfig(
        id="a",
        title="A",
        method="GET",
        url="https://lock-a.example/open",
        success_status=200,
        timeout_s=1,
    )
    lock = HttpLock(cfg)

    with aioresponses() as m:
        m.get("https://lock-a.example/open", exception=TimeoutError())
        result = await lock.open()

    assert result.ok is False
    assert "timeout" in result.detail.lower()


async def test_http_lock_open_connection_error_returns_failure() -> None:
    cfg = HttpLockConfig(
        id="a",
        title="A",
        method="GET",
        url="https://lock-a.example/open",
        success_status=200,
    )
    lock = HttpLock(cfg)

    with aioresponses() as m:
        m.get("https://lock-a.example/open", exception=ConnectionError("refused"))
        result = await lock.open()

    assert result.ok is False
    assert result.detail  # non-empty


async def test_http_lock_sends_headers_and_body() -> None:
    cfg = HttpLockConfig(
        id="a",
        title="A",
        method="POST",
        url="https://lock-a.example/open",
        headers={"X-Token": "t"},
        json_body={"cmd": "open"},
        success_status=200,
    )
    lock = HttpLock(cfg)

    with aioresponses() as m:
        m.post("https://lock-a.example/open", status=200)
        await lock.open()
        # verify request was made with our headers/body
        calls = m.requests[("POST", __import__("yarl").URL("https://lock-a.example/open"))]
        assert len(calls) == 1
        kwargs = calls[0].kwargs
        assert kwargs.get("headers", {}).get("X-Token") == "t"
        assert kwargs.get("json") == {"cmd": "open"}


def test_http_lock_config_rejects_unknown_method() -> None:
    with pytest.raises(ValueError):
        HttpLockConfig(id="a", title="A", method="WAT", url="https://x")
