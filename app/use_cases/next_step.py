"""Advance protocol or signal readiness for final rating."""

from __future__ import annotations

from dataclasses import dataclass

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from shared.dto import ErrorResult, ProtocolStepResult
from shared.locale import t


@dataclass(frozen=True, slots=True)
class NextStepOutcome:
    """Either next UI step or handoff to final self-rating."""

    kind: str  # "step" | "need_final_rating"
    step: ProtocolStepResult | None = None


class NextStepUseCase:
    """Move to next instruction or finish body of protocol."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def execute(self, user_id: int | str, *, locale: str = "ru") -> NextStepOutcome | ErrorResult:
        session = await load_session(self._ctx.users, user_id)
        if not session.protocol_id:
            return ErrorResult(
                code="no_protocol",
                message=t(locale, "next_no_protocol"),
            )
        pid = session.protocol_id
        variant_id = session.protocol_variant_id
        total = self._ctx.protocols.step_count(pid, variant_id=variant_id)
        idx = session.step_index
        if idx >= total:
            return ErrorResult(code="protocol_done", message=t(locale, "next_need_final"))

        if idx < total - 1:
            new_idx = idx + 1
            step = self._ctx.protocols.get_step(pid, new_idx, variant_id=variant_id)
            if not step:
                return ErrorResult(code="missing_step", message=t(locale, "next_missing_step"))
            session = session.with_updates(step_index=new_idx)
            await save_session(self._ctx.users, user_id, session)
            body = self._ctx.protocols.format_step_message(step, index=new_idx, total=total)
            pr = ProtocolStepResult(
                text=body,
                step_index=new_idx,
                total_steps=total,
                is_last_step=(new_idx == total - 1),
            )
            return NextStepOutcome(kind="step", step=pr)

        return NextStepOutcome(kind="need_final_rating", step=None)
