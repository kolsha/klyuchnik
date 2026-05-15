from __future__ import annotations

from typing import NamedTuple, Protocol, runtime_checkable


class LockResult(NamedTuple):
    """Outcome of a `Lock.open()` call, safe to surface to the user."""

    ok: bool
    detail: str
    battery_percent: int | None = None
    is_low_battery: bool = False


@runtime_checkable
class Lock(Protocol):
    """Common interface for every lock regardless of transport (HTTP, MQTT, GPIO, ...)."""

    @property
    def id(self) -> str: ...

    @property
    def title(self) -> str: ...

    async def open(self) -> LockResult: ...
