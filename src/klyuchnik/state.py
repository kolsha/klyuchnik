from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Protocol

_log = logging.getLogger(__name__)


class PinStateStore(Protocol):
    """Persists the id of the currently pinned welcome message per chat."""

    async def load(self, chat_id: int) -> int | None: ...
    async def save(self, chat_id: int, message_id: int) -> None: ...
    async def clear(self, chat_id: int) -> None: ...


class JsonPinStateStore:
    """Dead-simple JSON-file store. Fine for a single bot instance; swap for SQLite at scale."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def _read(self) -> dict[str, int]:
        if not self._path.is_file():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            return {str(k): int(v) for k, v in data.items()}
        except (OSError, ValueError) as exc:
            _log.warning("Pin state file %s unreadable (%s) — treating as empty", self._path, exc)
            return {}

    def _write(self, data: dict[str, int]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    async def load(self, chat_id: int) -> int | None:
        async with self._lock:
            return self._read().get(str(chat_id))

    async def save(self, chat_id: int, message_id: int) -> None:
        async with self._lock:
            data = self._read()
            data[str(chat_id)] = int(message_id)
            self._write(data)

    async def clear(self, chat_id: int) -> None:
        async with self._lock:
            data = self._read()
            data.pop(str(chat_id), None)
            self._write(data)
