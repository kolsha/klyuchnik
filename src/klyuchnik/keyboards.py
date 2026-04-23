from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from klyuchnik.locks.registry import LockRegistry


class LockCallback(CallbackData, prefix="lock"):
    action: str
    lock_id: str


def build_locks_keyboard(registry: LockRegistry) -> InlineKeyboardMarkup:
    """Build an inline keyboard with one button per lock, stacked vertically."""
    if len(registry) == 0:
        raise ValueError("LockRegistry is empty — cannot build keyboard")

    kb = InlineKeyboardBuilder()
    for lock in registry:
        kb.row(
            InlineKeyboardButton(
                text=lock.title,
                callback_data=LockCallback(action="open", lock_id=lock.id).pack(),
            )
        )
    return kb.as_markup()
