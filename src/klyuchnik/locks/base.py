from __future__ import annotations

from typing import NamedTuple, Protocol, runtime_checkable


class LockResult(NamedTuple):
    """Outcome of a `Lock.open()` call, safe to surface to the user."""

    ok: bool
    detail: str


@runtime_checkable
class Lock(Protocol):
    """Common interface for every lock regardless of transport (HTTP, MQTT, GPIO, ...)."""

    id: str
    title: str

    async def open(self) -> LockResult: ...
