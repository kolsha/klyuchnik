from __future__ import annotations

import logging
from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery

from klyuchnik.keyboards import LockCallback
from klyuchnik.locks.registry import LockRegistry
from klyuchnik.membership import MembershipChecker

_log = logging.getLogger(__name__)


async def handle_lock_open(
    *,
    callback: CallbackQuery | Any,
    lock_id: str,
    registry: LockRegistry,
    membership: MembershipChecker | Any,
) -> None:
    """Membership-gated dispatcher: verify → open → user-facing alert."""
    lock = registry.get(lock_id)
    if lock is None:
        _log.warning("Unknown lock id %r from user %s", lock_id, callback.from_user.id)
        await callback.answer("Неизвестный замок", show_alert=True)
        return

    user_id = callback.from_user.id
    if not await membership.is_member(user_id):
        _log.info("User %s is not a chat member — denying %s", user_id, lock_id)
        await callback.answer(
            "Доступ только для участников чата.", show_alert=True
        )
        return

    result = await lock.open()
    if result.ok:
        _log.info("Lock %s opened by user %s (%s)", lock.id, user_id, result.detail)
        await callback.answer(text=f"«{lock.title}» — открыто ✓")
    else:
        _log.warning("Lock %s failed for user %s: %s", lock.id, user_id, result.detail)
        await callback.answer(
            text=f"Не удалось открыть: {result.detail}", show_alert=True
        )


def build_callback_router(
    registry: LockRegistry,
    membership: MembershipChecker,
) -> Router:
    router = Router(name="locks")

    @router.callback_query(LockCallback.filter())
    async def _on_open(query: CallbackQuery, callback_data: LockCallback) -> None:
        if callback_data.action != "open":
            await query.answer()
            return
        await handle_lock_open(
            callback=query,
            lock_id=callback_data.lock_id,
            registry=registry,
            membership=membership,
        )

    return router
