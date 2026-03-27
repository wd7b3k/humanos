"""Start / reset session."""

from __future__ import annotations

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.constants import EVENT_START
from shared.dto import WelcomeResult
from shared.locale import render_state_previews_html, state_options_for, t


class StartUseCase:
    """Initialize or clear user flow after /start."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        user_id: int | str,
        *,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> WelcomeResult:
        """Reset session and return welcome copy + state choices."""
        self._ctx.analytics.track(EVENT_START, user_id, {"locale": locale}, app_type=app_type)
        existing = await load_session(self._ctx.users, user_id)
        fresh = existing.reset_flow()
        if fresh != existing:
            await save_session(self._ctx.users, user_id, fresh)
        previews = render_state_previews_html(locale)
        text = t(locale, "start_welcome", previews=previews)
        return WelcomeResult(text=text, state_labels=state_options_for(locale))
