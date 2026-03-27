"""Remove Telegram reply keyboard before inline-heavy messages (optional)."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, ReplyKeyboardRemove

from infrastructure.config import Settings

log = logging.getLogger(__name__)

# Minimal visible text; Telegram rejects empty. Deleted in background so the next send is not blocked.
_KB_STRIP_DOT = "·"


async def _delete_strip_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        log.debug("reply keyboard strip delete failed", exc_info=True)


async def maybe_strip_reply_keyboard(message: Message, settings: Settings) -> None:
    if not settings.bot_hide_reply_keyboard_outside_home:
        return
    strip = await message.answer(_KB_STRIP_DOT, reply_markup=ReplyKeyboardRemove())
    # Do not await delete: saves one round-trip before the real reply is sent.
    asyncio.create_task(_delete_strip_message(message.bot, message.chat.id, strip.message_id))
