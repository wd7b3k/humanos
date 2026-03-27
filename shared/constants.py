"""Application-wide constants (event names, state keys, rating bounds)."""

from __future__ import annotations

from shared.locale import (
    feedback_focus_options_for,
    final_rating_labels_for,
    initial_rating_labels_for,
    render_final_rating_guide as _render_final_rating_guide_loc,
    render_initial_rating_guide as _render_initial_rating_guide_loc,
    render_state_previews_html as _render_state_previews_loc,
    state_options_for,
    state_previews_for,
)

# Analytics event names
EVENT_START = "start"
EVENT_STATE_SELECTED = "state_selected"
EVENT_PROTOCOL_STARTED = "protocol_started"
EVENT_PROTOCOL_COMPLETED = "protocol_completed"
EVENT_IMPROVED = "improved"
EVENT_DONATION_SHOWN = "donation_shown"
EVENT_DONATION_CLICKED = "donation_clicked"
EVENT_PUSH_PERMISSION_SET = "push_permission_set"
EVENT_FEEDBACK_TOPIC_SELECTED = "feedback_topic_selected"
EVENT_FEEDBACK_MESSAGE_SENT = "feedback_message_sent"
EVENT_BOT_INTERACTION = "bot_interaction"
ANALYTICS_TRACE_EVENT_NAMES: frozenset[str] = frozenset({EVENT_BOT_INTERACTION})

# Default Russian labels (tests & code that omit locale)
STATE_OPTIONS: tuple[tuple[str, str], ...] = state_options_for("ru")
STATE_KEYS = frozenset(key for key, _ in STATE_OPTIONS)
STATE_PREVIEWS: dict[str, str] = state_previews_for("ru")

RATING_MIN = 1
RATING_MAX = 5

INITIAL_RATING_LABELS: tuple[tuple[int, str], ...] = initial_rating_labels_for("ru")
FINAL_RATING_LABELS: tuple[tuple[int, str], ...] = final_rating_labels_for("ru")

FEEDBACK_FOCUS_OPTIONS: tuple[tuple[str, str], ...] = feedback_focus_options_for("ru")
FEEDBACK_FOCUS_KEYS = frozenset(key for key, _ in FEEDBACK_FOCUS_OPTIONS)


def render_state_previews() -> str:
    """Russian previews (legacy); prefer ``render_state_previews_html(locale)`` in new code."""
    return _render_state_previews_loc("ru")


def render_state_previews_html(locale: str) -> str:
    return _render_state_previews_loc(locale)


def render_initial_rating_guide() -> str:
    return _render_initial_rating_guide_loc("ru")


def render_initial_rating_guide_locale(locale: str) -> str:
    return _render_initial_rating_guide_loc(locale)


def render_final_rating_guide() -> str:
    return _render_final_rating_guide_loc("ru")


def render_final_rating_guide_locale(locale: str) -> str:
    return _render_final_rating_guide_loc(locale)
