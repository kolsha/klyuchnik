from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int | None = None
    count: int = 0
    remaining: int | None = None


class RateLimiter(Protocol):
    async def check(self, *, lock_id: str, user_id: int) -> RateLimitDecision: ...
    async def record_success(self, *, lock_id: str, user_id: int) -> None: ...


class NullRateLimiter:
    async def check(self, *, lock_id: str, user_id: int) -> RateLimitDecision:
        return RateLimitDecision(allowed=True)

    async def record_success(self, *, lock_id: str, user_id: int) -> None:
        return None


_StoredLimits = dict[str, dict[str, dict[str, int]]]


class JsonDailyRateLimiter:
    """Persistent daily per-lock/per-user limiter for successful lock openings."""

    def __init__(
        self,
        path: Path,
        limits: Mapping[str, int],
        *,
        retention_days: int = 31,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._path = path
        self._limits = {lock_id: limit for lock_id, limit in limits.items() if limit > 0}
        self._retention_days = retention_days
        self._today = today
        self._lock = asyncio.Lock()

    async def check(self, *, lock_id: str, user_id: int) -> RateLimitDecision:
        limit = self._limits.get(lock_id)
        if limit is None:
            return RateLimitDecision(allowed=True)

        async with self._lock:
            data = self._read()
            data = self._prune(data)
            self._write(data)
            count = data.get(lock_id, {}).get(str(user_id), {}).get(self._today_key(), 0)

        remaining = max(limit - count, 0)
        return RateLimitDecision(
            allowed=count < limit,
            limit=limit,
            count=count,
            remaining=remaining,
        )

    async def record_success(self, *, lock_id: str, user_id: int) -> None:
        if lock_id not in self._limits:
            return

        async with self._lock:
            data = self._prune(self._read())
            user_counts = data.setdefault(lock_id, {}).setdefault(str(user_id), {})
            today_key = self._today_key()
            user_counts[today_key] = int(user_counts.get(today_key, 0)) + 1
            self._write(data)

    def _today_key(self) -> str:
        return self._today().isoformat()

    def _read(self) -> _StoredLimits:
        if not self._path.is_file():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            return self._normalize(data)
        except (OSError, ValueError, TypeError) as exc:
            _log.warning("Rate limit file %s unreadable (%s) - treating as empty", self._path, exc)
            return {}

    def _normalize(self, data: object) -> _StoredLimits:
        if not isinstance(data, dict):
            return {}

        normalized: _StoredLimits = {}
        for lock_id, users in data.items():
            if not isinstance(lock_id, str) or not isinstance(users, dict):
                continue
            normalized_users: dict[str, dict[str, int]] = {}
            for user_id, dates in users.items():
                if not isinstance(dates, dict):
                    continue
                normalized_dates: dict[str, int] = {}
                for day, count in dates.items():
                    if not isinstance(day, str):
                        continue
                    try:
                        normalized_dates[day] = int(count)
                    except (TypeError, ValueError):
                        continue
                if normalized_dates:
                    normalized_users[str(user_id)] = normalized_dates
            if normalized_users:
                normalized[lock_id] = normalized_users
        return normalized

    def _write(self, data: _StoredLimits) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def _prune(self, data: _StoredLimits) -> _StoredLimits:
        cutoff = self._today() - timedelta(days=self._retention_days)
        pruned: _StoredLimits = {}

        for lock_id, users in data.items():
            pruned_users: dict[str, dict[str, int]] = {}
            for user_id, dates in users.items():
                kept_dates: dict[str, int] = {}
                for day, count in dates.items():
                    parsed_day = self._parse_day(day)
                    if parsed_day is not None and parsed_day >= cutoff:
                        kept_dates[day] = count
                if kept_dates:
                    pruned_users[user_id] = kept_dates
            if pruned_users:
                pruned[lock_id] = pruned_users

        return pruned

    def _parse_day(self, value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
