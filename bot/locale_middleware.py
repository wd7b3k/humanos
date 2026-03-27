"""Inject ``locale`` (ru/en) from Telegram ``language_code`` into handler data."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update

from shared.locale import DEFAULT_LOCALE, normalize_locale


class LocaleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        locale = DEFAULT_LOCALE
        if isinstance(event, Update):
            u = None
            if event.message:
                u = event.message.from_user
            elif event.callback_query:
                u = event.callback_query.from_user
            elif event.edited_message:
                u = event.edited_message.from_user
            elif event.inline_query:
                u = event.inline_query.from_user
            elif event.my_chat_member:
                u = event.my_chat_member.from_user
            elif event.chat_member:
                u = event.chat_member.from_user
            if u is not None:
                locale = normalize_locale(u.language_code)
        data["locale"] = locale
        return await handler(event, data)
