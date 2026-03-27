"""Optional UX hints appended to protocol step bodies (locale-aware)."""

from __future__ import annotations

from shared.locale import t


def append_protocol_rating_hints(body: str, *, locale: str, step_index: int, total: int) -> str:
    """
    Short lines so users know the final rating screen is coming (reduces drop-off).
    No I/O; safe to call on every step render.
    """
    if total <= 0:
        return body
    extra: str | None = None
    if total == 1:
        extra = t(locale, "flow_proto_hint_then_rating")
    elif step_index == total - 1:
        extra = t(locale, "flow_proto_hint_then_rating")
    elif step_index == total - 2:
        extra = t(locale, "flow_proto_hint_one_step_left")
    if extra:
        return f"{body}\n\n<i>{extra}</i>"
    return body
