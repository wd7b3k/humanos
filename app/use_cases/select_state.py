"""Persist selected emotional/physical state."""

from __future__ import annotations

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.constants import EVENT_STATE_SELECTED, RATING_MAX, RATING_MIN, STATE_KEYS
from shared.dto import ErrorResult, StateSelectedResult
from shared.locale import render_initial_rating_guide, t


class SelectStateUseCase:
    """Validate state key and ask for initial self-rating."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        user_id: int | str,
        state_key: str,
        *,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> StateSelectedResult | ErrorResult:
        key = state_key.strip().lower()
        if key not in STATE_KEYS:
            return ErrorResult(
                code="unknown_state",
                message=t(locale, "err_unknown_state"),
            )
        session = (await load_session(self._ctx.users, user_id)).with_updates(
            selected_state=key,
            initial_rating=None,
            protocol_id=None,
            step_index=0,
            final_rating=None,
        )
        await save_session(self._ctx.users, user_id, session)
        self._ctx.analytics.track(
            EVENT_STATE_SELECTED,
            user_id,
            {"state": key, "locale": locale},
            app_type=app_type,
        )
        guide = render_initial_rating_guide(locale)
        text = t(
            locale,
            "select_state_prompt",
            rmin=RATING_MIN,
            rmax=RATING_MAX,
            guide=guide,
        )
        return StateSelectedResult(text=text, state_key=key)
