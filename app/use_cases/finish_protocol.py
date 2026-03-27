"""Compare before/after and prepare outcome + optional donation."""

from __future__ import annotations

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.constants import (
    EVENT_DONATION_SHOWN,
    EVENT_IMPROVED,
    EVENT_PROTOCOL_COMPLETED,
    RATING_MAX,
    RATING_MIN,
)
from shared.dto import ErrorResult, FinishResult
from shared.locale import t


class FinishProtocolUseCase:
    """Persist final rating, compute improvement, emit analytics."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    @staticmethod
    def _effect_guidance(*, improved: bool, final_rating: int, locale: str) -> list[str]:
        if improved:
            return [
                t(locale, "finish_guide_improved_1"),
                t(locale, "finish_guide_improved_2"),
            ]
        if final_rating == 1:
            return [t(locale, "finish_guide_calm_next")]
        return [
            t(locale, "finish_guide_flat_1"),
            t(locale, "finish_guide_flat_2"),
        ]

    async def execute(
        self,
        user_id: int | str,
        final_rating: int,
        *,
        app_type: str = "telegram",
        locale: str = "ru",
    ) -> FinishResult | ErrorResult:
        if final_rating < RATING_MIN or final_rating > RATING_MAX:
            return ErrorResult(
                code="invalid_rating",
                message=t(locale, "err_rating_range", min=RATING_MIN, max=RATING_MAX),
            )
        session = await load_session(self._ctx.users, user_id)
        if session.initial_rating is None:
            return ErrorResult(
                code="no_baseline",
                message=t(locale, "err_need_start_first"),
            )
        initial = session.initial_rating
        improved = final_rating < initial
        session = session.with_updates(final_rating=final_rating)
        await save_session(self._ctx.users, user_id, session)

        self._ctx.analytics.track(
            EVENT_PROTOCOL_COMPLETED,
            user_id,
            {
                "initial": initial,
                "final": final_rating,
                "improved": improved,
                "release_id": session.protocol_release_id,
                "release_version": session.protocol_release_version,
                "variant_id": session.protocol_variant_id,
                "locale": locale,
            },
            app_type=app_type,
        )
        if improved:
            self._ctx.analytics.track(
                EVENT_IMPROVED,
                user_id,
                {
                    "delta": final_rating - initial,
                    "release_id": session.protocol_release_id,
                    "release_version": session.protocol_release_version,
                    "variant_id": session.protocol_variant_id,
                    "locale": locale,
                },
                app_type=app_type,
            )

        lines = [
            t(locale, "finish_header"),
            t(
                locale,
                "finish_summary_line",
                initial=initial,
                final_rating=final_rating,
                mx=RATING_MAX,
            ),
            t(locale, "finish_scale_hint"),
        ]
        if improved:
            lines.append(t(locale, "finish_better"))
            self._ctx.analytics.track(
                EVENT_DONATION_SHOWN,
                user_id,
                {
                    "source": "finish_improved",
                    "release_id": session.protocol_release_id,
                    "release_version": session.protocol_release_version,
                    "variant_id": session.protocol_variant_id,
                    "locale": locale,
                },
                app_type=app_type,
            )
        elif final_rating == initial:
            lines.append(t(locale, "finish_same"))
        else:
            lines.append(t(locale, "finish_worse"))

        lines.extend(
            self._effect_guidance(
                improved=improved,
                final_rating=final_rating,
                locale=locale,
            )
        )

        text = "\n\n".join(lines)
        url = self._ctx.settings.tribute_url
        return FinishResult(
            text=text,
            initial_rating=initial,
            final_rating=final_rating,
            improved=improved,
            tribute_url=url,
        )
