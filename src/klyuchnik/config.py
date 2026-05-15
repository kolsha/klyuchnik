from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from klyuchnik.locks.http_lock import HttpLockConfig
from klyuchnik.locks.switchbot import SwitchbotLockConfig


class _LockSettingsBase(BaseSettings):
    """Config for one lock — picked up via env_prefix (LOCK_A_ / LOCK_B_)."""

    id: str
    title: str
    method: str = "POST"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    raw_body: str | None = None
    success_status: int = 200
    timeout_s: float = 10.0

    @field_validator("headers", mode="before")
    @classmethod
    def _parse_headers(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v) if v.strip() else {}
        return v

    @field_validator("json_body", mode="before")
    @classmethod
    def _parse_json_body(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v) if v.strip() else None
        return v

    def to_http_config(self) -> HttpLockConfig:
        return HttpLockConfig(
            id=self.id,
            title=self.title,
            method=self.method,
            url=self.url,
            headers=self.headers,
            json_body=self.json_body,
            raw_body=self.raw_body,
            success_status=self.success_status,
            timeout_s=self.timeout_s,
        )


class LockASettings(_LockSettingsBase):
    model_config = SettingsConfigDict(
        env_prefix="LOCK_A_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class LockBSettings(_LockSettingsBase):
    model_config = SettingsConfigDict(
        env_prefix="LOCK_B_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class SwitchbotLockSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOCK_B_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    id: str
    title: str
    base_url: str
    timeout_s: float = 10.0
    rate_limit_daily_open_limit: int = 10

    def to_switchbot_config(self) -> SwitchbotLockConfig:
        return SwitchbotLockConfig(
            id=self.id,
            title=self.title,
            base_url=self.base_url,
            timeout_s=self.timeout_s,
        )


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: SecretStr
    chat_id: int
    state_file: Path = Path("./state.json")
    membership_ttl_s: float = 60.0
    content_dir: Path = Path("./content")
    rate_limit_file: Path = Path("./lock_rate_limits.json")
    rate_limit_retention_days: int = 7
    rate_limit_excluded_user_ids: set[int] = Field(default_factory=set)

    @field_validator("rate_limit_excluded_user_ids", mode="before")
    @classmethod
    def _parse_rate_limit_excluded_user_ids(cls, v: Any) -> Any:
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return set()
            if raw.startswith("["):
                return set(json.loads(raw))
            return {int(part.strip()) for part in raw.split(",") if part.strip()}
        return v


class Settings:
    """Composite settings: top-level app + two locks pulled via prefixes."""

    def __init__(
        self,
        app: AppSettings | None = None,
        lock_a: _LockSettingsBase | None = None,
        lock_b: SwitchbotLockSettings | None = None,
    ) -> None:
        self.app = app or AppSettings()  # type: ignore[call-arg]
        self.lock_a = lock_a or LockASettings()  # type: ignore[call-arg]
        self.lock_b = lock_b or SwitchbotLockSettings()  # type: ignore[call-arg]
