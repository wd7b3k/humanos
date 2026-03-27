"""Rate-limited уведомления админам об ошибках обработчиков (prod)."""

from __future__ import annotations

import asyncio
import html
import logging
import time

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent

from infrastructure.config import Settings
from shared.locale import t

log = logging.getLogger(__name__)


def _should_alert_for_exception(exc: BaseException) -> bool:
    if isinstance(exc, TelegramForbiddenError):
        return False
    if isinstance(exc, TelegramBadRequest):
        lowered = str(exc).lower()
        for phrase in (
            "message is not modified",
            "query is too old",
            "query id is invalid",
            "message to delete not found",
            "message can't be deleted",
            "chat not found",
            "user is deactivated",
            "bot was blocked",
            "have no rights",
        ):
            if phrase in lowered:
                return False
    return True


def register_admin_error_alerts(dp: Dispatcher, bot: Bot, settings: Settings, *, min_interval_seconds: float = 55.0) -> None:
    """Регистрирует глобальный обработчик ошибок с анти-спамом для админов."""

    if not settings.admin_ids:
        return

    last_alert_at = 0.0
    lock = asyncio.Lock()

    async def _on_error(event: ErrorEvent) -> bool:
        nonlocal last_alert_at
        exc = event.exception
        log.exception("update handler failed: %s", exc)

        if not _should_alert_for_exception(exc):
            return True

        now = time.monotonic()
        async with lock:
            if now - last_alert_at < min_interval_seconds:
                return True
            last_alert_at = now

        title = html.escape(type(exc).__name__)
        detail = html.escape(str(exc)[:500])
        text = t("ru", "admin_error_alert", title=title, detail=detail)
        for admin_id in sorted(settings.admin_ids):
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                log.exception("admin error alert failed for %s", admin_id)
        return True

    dp.errors.register(_on_error)
