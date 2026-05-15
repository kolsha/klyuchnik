from __future__ import annotations

import pytest
from aioresponses import aioresponses

from klyuchnik.locks.base import Lock, LockResult
from klyuchnik.locks.switchbot import SwitchbotLock, SwitchbotLockConfig


def test_switchbot_lock_implements_protocol() -> None:
    lock: Lock = SwitchbotLock(
        SwitchbotLockConfig(id="b", title="Door", base_url="http://lock.local"),
    )

    assert lock.id == "b"
    assert lock.title == "Door"


async def test_switchbot_lock_unlock_posts_empty_body_and_reports_battery() -> None:
    lock = SwitchbotLock(
        SwitchbotLockConfig(id="b", title="Door", base_url="http://lock.local/"),
    )

    with aioresponses() as m:
        m.post(
            "http://lock.local/unlock",
            status=200,
            payload={
                "lock_state": "unlocking",
                "door_state": "closed",
                "battery_percent": 20,
                "is_low_battery": True,
            },
        )
        result = await lock.open()

        calls = m.requests[("POST", __import__("yarl").URL("http://lock.local/unlock"))]

    assert isinstance(result, LockResult)
    assert result.ok is True
    assert "unlocking" in result.detail
    assert result.battery_percent == 20
    assert result.is_low_battery is True
    assert len(calls) == 1
    assert calls[0].kwargs.get("data") == ""


async def test_switchbot_lock_http_error_returns_failure_with_body() -> None:
    lock = SwitchbotLock(
        SwitchbotLockConfig(id="b", title="Door", base_url="http://lock.local"),
    )

    with aioresponses() as m:
        m.post("http://lock.local/unlock", status=500, body="boom")
        result = await lock.open()

    assert result.ok is False
    assert "500" in result.detail
    assert "boom" in result.detail


async def test_switchbot_lock_invalid_json_returns_failure() -> None:
    lock = SwitchbotLock(
        SwitchbotLockConfig(id="b", title="Door", base_url="http://lock.local"),
    )

    with aioresponses() as m:
        m.post("http://lock.local/unlock", status=200, body="not json")
        result = await lock.open()

    assert result.ok is False
    assert "json" in result.detail.lower()


async def test_switchbot_lock_timeout_returns_failure() -> None:
    lock = SwitchbotLock(
        SwitchbotLockConfig(id="b", title="Door", base_url="http://lock.local", timeout_s=1),
    )

    with aioresponses() as m:
        m.post("http://lock.local/unlock", exception=TimeoutError())
        result = await lock.open()

    assert result.ok is False
    assert "timeout" in result.detail.lower()


def test_switchbot_lock_config_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        SwitchbotLockConfig(id="b", title="Door", base_url="")
