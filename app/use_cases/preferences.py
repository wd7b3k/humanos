"""User preferences, push permission and feedback capture."""

from __future__ import annotations

from datetime import UTC, datetime

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.constants import (
    EVENT_FEEDBACK_MESSAGE_SENT,
    EVENT_FEEDBACK_TOPIC_SELECTED,
    EVENT_PUSH_PERMISSION_SET,
    FEEDBACK_FOCUS_KEYS,
)
from shared.dto import ErrorResult
from shared.locale import t


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class PreferencesUseCase:
    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def set_push_permission(
        self,
        user_id: int | str,
        *,
        allowed: bool,
        app_type: str = "telegram",
    ) -> bool:
        session = await load_session(self._ctx.users, user_id)
        updated = session.with_updates(
            push_permission_telegram=allowed,
            push_permission_answered_at=_now_iso(),
            auth_provider="telegram",
            auth_subject=str(user_id),
        )
        await save_session(self._ctx.users, user_id, updated)
        self._ctx.analytics.track(
            EVENT_PUSH_PERMISSION_SET,
            user_id,
            {"channel": "telegram", "allowed": allowed},
            app_type=app_type,
        )
        return allowed

    async def add_feedback_topic(
        self,
        user_id: int | str,
        topic_key: str,
        *,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> tuple[str, ...] | ErrorResult:
        key = topic_key.strip().lower()
        if key not in FEEDBACK_FOCUS_KEYS:
            return ErrorResult(code="unknown_feedback_topic", message=t(locale, "prefs_unknown_topic"))
        session = await load_session(self._ctx.users, user_id)
        topics = tuple(dict.fromkeys([*session.feedback_topics, key]))
        updated = session.with_updates(feedback_topics=topics)
        await save_session(self._ctx.users, user_id, updated)
        self._ctx.analytics.track(
            EVENT_FEEDBACK_TOPIC_SELECTED,
            user_id,
            {"topic": key, "locale": locale},
            app_type=app_type,
        )
        return topics

    async def save_feedback_message(
        self,
        user_id: int | str,
        text: str,
        *,
        username: str | None = None,
        full_name: str | None = None,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> str | ErrorResult:
        normalized = " ".join((text or "").split())
        if len(normalized) < 3:
            return ErrorResult(
                code="feedback_too_short",
                message=t(locale, "prefs_feedback_empty"),
            )
        session = await load_session(self._ctx.users, user_id)
        updated = session.with_updates(feedback_last_message_at=_now_iso())
        await save_session(self._ctx.users, user_id, updated)
        await self._ctx.feedback_store.append(
            user_id=user_id,
            text=normalized,
            username=username,
            full_name=full_name,
        )
        self._ctx.analytics.track(
            EVENT_FEEDBACK_MESSAGE_SENT,
            user_id,
            {"length": len(normalized), "locale": locale},
            app_type=app_type,
        )
        return normalized
