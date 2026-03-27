"""Telegram Bot API guardrails: empty / HTML-collapsed text and callback answers."""

from __future__ import annotations

import logging
import re
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")

# Символы, которые клиент / сервер Telegram часто считают «пустым» текстом.
_INVISIBLE_TRANSL = str.maketrans(
    "",
    "",
    "\u200b\u200c\u200d\ufeff\u2060\u2061\u2062\u2063\u200e\u200f\u2800\u00ad",
)


def _strip_invisible(s: str) -> str:
    return (s or "").translate(_INVISIBLE_TRANSL).strip()


def visible_plain_from_html(html: str) -> str:
    """Rough visible text after tags + common entities (Telegram HTML)."""
    s = _TAG_RE.sub("", html or "")
    for a, b in (
        ("&nbsp;", " "),
        ("&#39;", "'"),
        ("&quot;", '"'),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&amp;", "&"),
    ):
        s = s.replace(a, b)
    return _strip_invisible(s)


def ensure_html_message(
    text: str | None,
    *,
    fallback: str | None = None,
    locale: str | None = None,
) -> str:
    """sendMessage / editMessageText: non-empty after strip and after tag removal."""
    from shared.locale import normalize_locale, t

    raw = (text or "").strip()
    if not raw:
        return fallback if fallback is not None else t(normalize_locale(locale), "generic_error")
    if not visible_plain_from_html(raw):
        return fallback if fallback is not None else t(normalize_locale(locale), "generic_error")
    return raw


def html_message_and_caption(
    text: str | None,
    *,
    empty_fallback: str | None = None,
    locale: str | None = None,
) -> tuple[str, str | None]:
    """
    Text path + optional photo caption.
    Caption omitted when there is no visible content (avoids Bad Request on empty caption).
    """
    from shared.locale import normalize_locale, t

    fb = empty_fallback if empty_fallback is not None else t(normalize_locale(locale), "empty_fallback")
    raw = (text or "").strip()
    if not raw:
        return fb, None
    if not visible_plain_from_html(raw):
        return fb, None
    return raw, raw


async def safe_answer_callback(
    query: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
    url: str | None = None,
    cache_time: int | None = None,
) -> None:
    """answerCallbackQuery: never send empty text; alerts must have non-empty copy."""
    from shared.locale import t as tr

    try:
        if url is not None:
            await query.answer(url=url, cache_time=cache_time)
            return
        msg = (text or "").strip()
        if show_alert:
            fb = tr("ru", "generic_error")
            msg = msg or fb
            if not visible_plain_from_html(msg):
                msg = fb
            await query.answer(text=msg[:200], show_alert=True, cache_time=cache_time)
            return
        if not msg or not visible_plain_from_html(msg):
            await query.answer(cache_time=cache_time)
            return
        await query.answer(text=msg[:200], cache_time=cache_time)
    except TelegramBadRequest as exc:
        raw = str(exc).lower()
        if "query is too old" in raw or "query id is invalid" in raw:
            log.info("stale callback answer ignored: %s", raw)
            return
        if "text must be non-empty" in raw:
            try:
                await query.answer(cache_time=cache_time)
            except TelegramBadRequest:
                log.info("callback answer fallback failed", exc_info=True)
            return
        raise


def install_callback_query_answer_guard() -> None:
    """
    Патчит CallbackQuery.answer: пустой / «невидимый» text не уходит в API
    (в т.ч. вызовы из сторонних хелперов и будущий код).
    """
    from aiogram.types import CallbackQuery as CQ

    if getattr(CQ.answer, "_humanos_telegram_guard", False):
        return

    _orig = CQ.answer

    def answer(
        self: CallbackQuery,
        text: str | None = None,
        show_alert: bool | None = None,
        url: str | None = None,
        cache_time: int | None = None,
        **kwargs: Any,
    ):
        from shared.locale import t as tr

        fb = tr("ru", "generic_error")
        if url is not None:
            return _orig(self, text=text, show_alert=show_alert, url=url, cache_time=cache_time, **kwargs)
        alert = bool(show_alert)
        if text is not None:
            cand = text.strip()
            if not cand or not visible_plain_from_html(cand):
                if alert:
                    cand = fb
                else:
                    return _orig(
                        self,
                        text=None,
                        show_alert=show_alert,
                        url=None,
                        cache_time=cache_time,
                        **kwargs,
                    )
            text = cand[:200]
        elif alert:
            text = fb
        return _orig(
            self,
            text=text,
            show_alert=show_alert,
            url=None,
            cache_time=cache_time,
            **kwargs,
        )

    answer._humanos_telegram_guard = True  # type: ignore[attr-defined]
    CQ.answer = answer  # type: ignore[method-assign]
