"""Record per-update interaction traces (non-blocking, after successful handling)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, Update

from app.use_cases.context import AppContext
from shared.constants import EVENT_BOT_INTERACTION
from shared.locale import (
    SUPPORTED_LOCALES,
    feedback_focus_options_for,
    initial_rating_labels_for,
    state_options_for,
    t,
)

log = logging.getLogger(__name__)

_MAX_CALLBACK_DATA = 96
_MAX_COMMAND = 48

_REPLY_TEXT_TO_SLUG: dict[str, str] = {}
for _loc in SUPPORTED_LOCALES:
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_start")] = "reply_start"
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_about")] = "reply_about"
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_donate")] = "reply_donate"
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_admin")] = "reply_admin"
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_admin_restart")] = "reply_admin_restart"
    _REPLY_TEXT_TO_SLUG[t(_loc, "btn_feedback")] = "reply_feedback"
    _REPLY_TEXT_TO_SLUG[t(_loc, "kb_nav_home")] = "reply_nav_home"
for _loc in SUPPORTED_LOCALES:
    for _key, _label in state_options_for(_loc):
        _REPLY_TEXT_TO_SLUG[_label] = f"state_pick_{_key}"
    for _score, _label in initial_rating_labels_for(_loc):
        _REPLY_TEXT_TO_SLUG[_label] = f"rating_reply_{_score}"
    for _key, _label in feedback_focus_options_for(_loc):
        _REPLY_TEXT_TO_SLUG[_label] = f"feedback_topic_{_key}"


def _attachment_summary(message: Message) -> str:
    parts: list[str] = []
    if message.photo:
        parts.append("photo")
    if message.document:
        parts.append("document")
    if message.voice:
        parts.append("voice")
    if message.video:
        parts.append("video")
    if message.audio:
        parts.append("audio")
    if message.sticker:
        parts.append("sticker")
    if message.location:
        parts.append("location")
    if message.contact:
        parts.append("contact")
    if message.poll:
        parts.append("poll")
    if message.video_note:
        parts.append("video_note")
    if message.animation:
        parts.append("animation")
    return ",".join(parts) if parts else "other"


def _payload_for_update(update: Update) -> tuple[int, dict[str, Any]] | None:
    if update.message and update.message.from_user:
        m = update.message
        uid = m.from_user.id
        if m.text is not None:
            text = m.text
            if text.startswith("/"):
                cmd = text.split(maxsplit=1)[0]
                return uid, {"kind": "command", "command": cmd[:_MAX_COMMAND]}
            slug = _REPLY_TEXT_TO_SLUG.get(text.strip())
            if slug:
                return uid, {"kind": "reply_button", "slug": slug}
            return uid, {"kind": "text", "len": len(text)}
        if m.caption:
            return uid, {"kind": "caption", "len": len(m.caption)}
        return uid, {"kind": "attachment", "types": _attachment_summary(m)}

    if update.callback_query and update.callback_query.from_user:
        cq = update.callback_query
        data = cq.data or ""
        prefix = data.split(":", 1)[0] if data else ""
        return cq.from_user.id, {
            "kind": "callback",
            "prefix": prefix[:48],
            "data": data[:_MAX_CALLBACK_DATA],
        }

    if update.edited_message and update.edited_message.from_user:
        em = update.edited_message
        if em.text is not None:
            return em.from_user.id, {"kind": "edited_text", "len": len(em.text)}
        if em.caption:
            return em.from_user.id, {"kind": "edited_caption", "len": len(em.caption)}
        return em.from_user.id, {"kind": "edited_message", "types": _attachment_summary(em)}

    return None


class BotInteractionAnalyticsMiddleware(BaseMiddleware):
    """
    Tracks inbound Telegram updates as ``EVENT_BOT_INTERACTION`` (JSONL + buffer).

    Payload always includes ``locale`` when ``LocaleMiddleware`` ran (Telegram UI language).
    Funnel events (``start``, ``state_selected``, …) are logged separately in use cases.
    """

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        if not isinstance(event, Update):
            return result

        ev = event
        locale_hint = data.get("locale")
        ctx = self._ctx

        def _log_task_err(task: asyncio.Task) -> None:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                log.debug("bot_interaction analytics task failed", exc_info=True)

        async def _persist_trace() -> None:
            try:
                parsed = _payload_for_update(ev)
                if parsed is None:
                    return
                user_id, payload = parsed
                if locale_hint is not None:
                    payload = {**payload, "locale": str(locale_hint)}
                ctx.analytics.track(EVENT_BOT_INTERACTION, user_id, payload, app_type="telegram")
            except Exception:
                log.debug("bot_interaction analytics failed", exc_info=True)

        t = asyncio.create_task(_persist_trace())
        t.add_done_callback(_log_task_err)
        return result
