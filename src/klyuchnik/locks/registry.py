from __future__ import annotations

from collections.abc import Iterable, Iterator

from klyuchnik.locks.base import Lock


class LockRegistry:
    """Keeps locks addressable by a short stable id used in callback data."""

    def __init__(self, locks: Iterable[Lock]) -> None:
        self._locks: dict[str, Lock] = {}
        for lock in locks:
            if lock.id in self._locks:
                raise ValueError(f"Duplicate lock id: {lock.id!r}")
            self._locks[lock.id] = lock

    def get(self, lock_id: str) -> Lock | None:
        return self._locks.get(lock_id)

    def __iter__(self) -> Iterator[Lock]:
        return iter(self._locks.values())

    def __len__(self) -> int:
        return len(self._locks)
