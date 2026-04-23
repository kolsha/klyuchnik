from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from klyuchnik.locks.base import LockResult

_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HttpLockConfig:
    id: str
    title: str
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    raw_body: str | None = None
    success_status: int = 200
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        method = self.method.upper()
        if method not in _ALLOWED_METHODS:
            raise ValueError(
                f"Unsupported HTTP method {self.method!r}; allowed: {sorted(_ALLOWED_METHODS)}"
            )
        object.__setattr__(self, "method", method)


class HttpLock:
    """A `Lock` whose `open()` triggers a configurable HTTP request.

    Two concrete locks with different URLs/methods/headers share this class —
    they differ only in configuration, which keeps the interface uniform.
    """

    def __init__(
        self,
        config: HttpLockConfig,
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
        try:
            async with self._session_factory(timeout=timeout) as session:
                kwargs: dict[str, Any] = {"headers": cfg.headers}
                if cfg.json_body is not None:
                    kwargs["json"] = cfg.json_body
                elif cfg.raw_body is not None:
                    kwargs["data"] = cfg.raw_body

                async with session.request(cfg.method, cfg.url, **kwargs) as resp:
                    if resp.status == cfg.success_status:
                        return LockResult(ok=True, detail=f"HTTP {resp.status}")
                    body = await resp.text()
                    return LockResult(
                        ok=False,
                        detail=f"HTTP {resp.status}: {body[:200]}",
                    )
        except TimeoutError:
            _log.warning("Lock %s HTTP timeout after %ss", cfg.id, cfg.timeout_s)
            return LockResult(ok=False, detail=f"timeout after {cfg.timeout_s}s")
        except aiohttp.ClientError as exc:
            _log.warning("Lock %s HTTP client error: %s", cfg.id, exc)
            return LockResult(ok=False, detail=f"connection error: {exc}")
        except Exception as exc:
            # Never let a broken lock kill the handler; surface it to the user.
            _log.exception("Lock %s unexpected error", cfg.id)
            return LockResult(ok=False, detail=f"unexpected error: {exc}")
