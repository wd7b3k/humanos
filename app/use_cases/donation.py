"""Track donation CTA taps before opening TRIBUTE_URL."""

from __future__ import annotations

from urllib.parse import urlencode

from app.session_util import load_session
from app.use_cases.context import AppContext
from shared.constants import EVENT_DONATION_CLICKED
from shared.dto import DonationTrackResult


class DonationUseCase:
    """Log donation CTA tap source; URL is always ``TRIBUTE_URL``."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    def build_redirect_url(self, user_id: int | str, source: str, *, app_type: str = "telegram") -> str:
        base_url = self._ctx.settings.public_http_base_url
        if not base_url:
            return self._ctx.settings.tribute_url
        query = urlencode(
            {
                "user_id": str(user_id),
                "source": (source or "").strip() or "unknown",
                "app_type": (app_type or "").strip() or "unknown",
            }
        )
        return f"{base_url}/r/donate?{query}"

    async def execute(
        self,
        user_id: int | str,
        source: str,
        *,
        app_type: str = "telegram",
        locale: str | None = None,
    ) -> DonationTrackResult:
        normalized_source = (source or "").strip() or "unknown"
        session = await load_session(self._ctx.users, user_id)
        payload: dict[str, object | None] = {
            "source": normalized_source,
            "release_id": session.protocol_release_id,
            "release_version": session.protocol_release_version,
            "variant_id": session.protocol_variant_id,
        }
        if locale is not None:
            payload["locale"] = locale
        self._ctx.analytics.track(
            EVENT_DONATION_CLICKED,
            user_id,
            payload,
            app_type=app_type,
        )
        return DonationTrackResult(url=self._ctx.settings.tribute_url, source=normalized_source)
