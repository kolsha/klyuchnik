from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from klyuchnik.locks.base import LockResult

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwitchbotLockConfig:
    id: str
    title: str
    base_url: str
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError("Switchbot base_url must not be empty")
        object.__setattr__(self, "base_url", base_url)


class SwitchbotLock:
    """SwitchBot Lock HTTP proxy client.

    The proxy expects POST requests with an empty body for commands and returns
    the lock state as JSON, including battery details.
    """

    def __init__(
        self,
        config: SwitchbotLockConfig,
        session_factory: type[aiohttp.ClientSession] = aiohttp.ClientSession,
    ) -> None:
        self._config = config
        self._session_factory = session_factory

    @property
    def id(self) -> str:
        return self._config.id

    @property
    def title(self) -> str:
        return self._config.title

    async def open(self) -> LockResult:
        cfg = self._config
        timeout = aiohttp.ClientTimeout(total=cfg.timeout_s)
        url = f"{cfg.base_url}/unlock"
        try:
            async with (
                self._session_factory(timeout=timeout) as session,
                session.post(url, data="") as resp,
            ):
                if resp.status != 200:
                    body = await resp.text()
                    return LockResult(
                        ok=False,
                        detail=f"HTTP {resp.status}: {body[:200]}",
                    )
                try:
                    payload = await resp.json()
                except (aiohttp.ContentTypeError, ValueError) as exc:
                    return LockResult(ok=False, detail=f"invalid JSON response: {exc}")
        except TimeoutError:
            _log.warning("Switchbot lock %s HTTP timeout after %ss", cfg.id, cfg.timeout_s)
            return LockResult(ok=False, detail=f"timeout after {cfg.timeout_s}s")
        except aiohttp.ClientError as exc:
            _log.warning("Switchbot lock %s HTTP client error: %s", cfg.id, exc)
            return LockResult(ok=False, detail=f"connection error: {exc}")
        except Exception as exc:
            _log.exception("Switchbot lock %s unexpected error", cfg.id)
            return LockResult(ok=False, detail=f"unexpected error: {exc}")

        if not isinstance(payload, dict):
            return LockResult(ok=False, detail="invalid JSON response: expected object")

        return self._result_from_payload(payload)

    def _result_from_payload(self, payload: dict[str, Any]) -> LockResult:
        lock_state = payload.get("lock_state", "unknown")
        door_state = payload.get("door_state", "unknown")
        battery_percent = payload.get("battery_percent")
        is_low_battery = payload.get("is_low_battery")

        return LockResult(
            ok=True,
            detail=f"lock={lock_state}, door={door_state}",
            battery_percent=battery_percent if isinstance(battery_percent, int) else None,
            is_low_battery=is_low_battery if isinstance(is_low_battery, bool) else False,
        )
