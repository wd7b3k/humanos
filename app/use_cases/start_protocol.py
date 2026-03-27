"""Begin protocol after initial numeric rating."""

from __future__ import annotations

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.constants import EVENT_PROTOCOL_STARTED, RATING_MAX, RATING_MIN
from shared.dto import ErrorResult, ProtocolStartResult, ProtocolStepResult
from shared.locale import t
from shared.protocol_step_hints import append_protocol_rating_hints


class StartProtocolUseCase:
    """Store initial rating, resolve protocol, return first step."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        user_id: int | str,
        initial_rating: int,
        *,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> ProtocolStartResult | ErrorResult:
        if initial_rating < RATING_MIN or initial_rating > RATING_MAX:
            return ErrorResult(
                code="invalid_rating",
                message=t(locale, "err_rating_range", min=RATING_MIN, max=RATING_MAX),
            )
        session = await load_session(self._ctx.users, user_id)
        if not session.selected_state:
            return ErrorResult(
                code="no_state",
                message=t(locale, "start_proto_need_state"),
            )
        protocol_id = self._ctx.protocols.resolve_protocol_id(session.selected_state)
        variant_id = self._ctx.protocols.choose_variant(protocol_id)
        release_meta = self._ctx.protocols.current_release()
        total = self._ctx.protocols.step_count(protocol_id, variant_id=variant_id)
        if total == 0:
            return ErrorResult(code="empty_protocol", message=t(locale, "start_proto_empty"))

        step0 = self._ctx.protocols.get_step(protocol_id, 0, variant_id=variant_id)
        if not step0:
            return ErrorResult(code="missing_step", message=t(locale, "start_proto_missing_step"))

        session = session.with_updates(
            initial_rating=initial_rating,
            protocol_id=protocol_id,
            protocol_release_id=str(release_meta["release_id"]),
            protocol_release_version=str(release_meta["release_version"]),
            protocol_variant_id=variant_id,
            step_index=0,
            final_rating=None,
        )
        await save_session(self._ctx.users, user_id, session)
        self._ctx.analytics.track(
            EVENT_PROTOCOL_STARTED,
            user_id,
            {
                "protocol_id": protocol_id,
                "initial_rating": initial_rating,
                "release_id": str(release_meta["release_id"]),
                "release_version": str(release_meta["release_version"]),
                "variant_id": variant_id,
                "locale": locale,
            },
            app_type=app_type,
        )
        body = self._ctx.protocols.format_step_message(step0, index=0, total=total)
        body = append_protocol_rating_hints(body, locale=locale, step_index=0, total=total)
        first = ProtocolStepResult(
            text=body,
            step_index=0,
            total_steps=total,
            is_last_step=(total == 1),
            protocol_id=protocol_id,
        )
        return ProtocolStartResult(first_step=first)
