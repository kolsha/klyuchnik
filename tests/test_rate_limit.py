from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from klyuchnik.rate_limit import JsonDailyRateLimiter, NullRateLimiter


async def test_null_rate_limiter_allows_and_does_not_record() -> None:
    limiter = NullRateLimiter()

    decision = await limiter.check(lock_id="a", user_id=42)
    await limiter.record_success(lock_id="a", user_id=42)

    assert decision.allowed is True
    assert decision.limit is None
    assert decision.remaining is None


async def test_daily_rate_limiter_limits_per_lock_and_user(tmp_path: Path) -> None:
    limiter = JsonDailyRateLimiter(
        path=tmp_path / "limits.json",
        limits={"b": 2},
        today=lambda: date(2026, 5, 15),
    )

    assert (await limiter.check(lock_id="b", user_id=1)).allowed is True
    await limiter.record_success(lock_id="b", user_id=1)
    await limiter.record_success(lock_id="b", user_id=1)

    assert (await limiter.check(lock_id="b", user_id=1)).allowed is False
    assert (await limiter.check(lock_id="b", user_id=2)).allowed is True
    assert (await limiter.check(lock_id="a", user_id=1)).allowed is True


async def test_daily_rate_limiter_resets_by_date(tmp_path: Path) -> None:
    current_day = date(2026, 5, 15)
    limiter = JsonDailyRateLimiter(
        path=tmp_path / "limits.json",
        limits={"b": 1},
        today=lambda: current_day,
    )

    await limiter.record_success(lock_id="b", user_id=1)
    assert (await limiter.check(lock_id="b", user_id=1)).allowed is False

    current_day = date(2026, 5, 16)
    assert (await limiter.check(lock_id="b", user_id=1)).allowed is True


async def test_daily_rate_limiter_prunes_old_entries(tmp_path: Path) -> None:
    path = tmp_path / "limits.json"
    path.write_text(
        json.dumps(
            {
                "b": {
                    "1": {"2026-05-14": 1},
                    "2": {"2026-04-01": 1},
                },
                "c": {"3": {"2026-04-01": 1}},
            }
        ),
        encoding="utf-8",
    )
    limiter = JsonDailyRateLimiter(
        path=path,
        limits={"b": 10, "c": 10},
        retention_days=31,
        today=lambda: date(2026, 5, 15),
    )

    await limiter.check(lock_id="b", user_id=1)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"b": {"1": {"2026-05-14": 1}}}


async def test_daily_rate_limiter_ignores_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "limits.json"
    path.write_text("not json", encoding="utf-8")
    limiter = JsonDailyRateLimiter(
        path=path,
        limits={"b": 1},
        today=lambda: date(2026, 5, 15),
    )

    assert (await limiter.check(lock_id="b", user_id=1)).allowed is True
