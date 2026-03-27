"""Capture transport identities for cross-channel account recovery."""

from __future__ import annotations

from datetime import UTC, datetime

from domain.client_models import ROLE_ADMIN, ROLE_CLIENT
from app.session_util import load_session, save_session
from app.use_cases.context import AppContext


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _coerce_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class IdentityCaptureUseCase:
    """Persist Telegram identity hints for future auth on other clients."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def sync_telegram_identity(
        self,
        *,
        user_id: int | str,
        username: str | None,
        full_name: str | None,
        language_code: str | None,
    ) -> None:
        session = await load_session(self._ctx.users, user_id)
        public_id = (username or "").strip() or None
        public_url = f"https://t.me/{public_id}" if public_id else None
        normalized_full_name = (full_name or "").strip() or None
        normalized_language_code = (language_code or "").strip() or None
        identity_changed = any(
            [
                session.auth_provider != "telegram",
                session.auth_subject != str(user_id),
                session.telegram_internal_id != str(user_id),
                session.telegram_public_id != public_id,
                session.telegram_username != public_id,
                session.telegram_profile_url != public_url,
                session.telegram_full_name != normalized_full_name,
                session.telegram_language_code != normalized_language_code,
            ]
        )
        last_seen = _coerce_ts(session.telegram_last_seen_at)
        should_refresh_last_seen = (
            last_seen is None or (datetime.now(UTC) - last_seen).total_seconds() >= 900
        )
        if not identity_changed and not should_refresh_last_seen:
            return
        client = await self._ctx.clients.upsert_identity(
            provider="telegram",
            subject=str(user_id),
            username=public_id,
            display_name=normalized_full_name,
            profile_url=public_url,
            last_seen_at=_now_iso(),
            role=ROLE_ADMIN if self._ctx.settings.is_admin(user_id) else ROLE_CLIENT,
        )
        updated = session.with_updates(
            auth_provider="telegram",
            auth_subject=str(user_id),
            telegram_internal_id=str(user_id),
            telegram_public_id=public_id,
            telegram_username=public_id,
            telegram_profile_url=public_url,
            telegram_full_name=normalized_full_name,
            telegram_language_code=normalized_language_code,
            telegram_last_seen_at=_now_iso() if should_refresh_last_seen else session.telegram_last_seen_at,
            client_id=client.client_id,
        )
        await save_session(self._ctx.users, user_id, updated)
