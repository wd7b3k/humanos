"""Resolve Telegram language_code → ru/en and fetch translated UI copy."""

from __future__ import annotations

from shared.locale_catalog import FEEDBACK_ORDER, MESSAGES, STATE_ORDER

SUPPORTED_LOCALES: frozenset[str] = frozenset(MESSAGES.keys())
DEFAULT_LOCALE = "ru"


def normalize_locale(language_code: str | None) -> str:
    if not language_code or not str(language_code).strip():
        return DEFAULT_LOCALE
    primary = str(language_code).strip().lower().split("-", 1)[0]
    return primary if primary in SUPPORTED_LOCALES else DEFAULT_LOCALE


def t(locale: str, key: str, **kwargs: object) -> str:
    """Translated string; falls back to Russian; then to key if missing."""
    loc = normalize_locale(locale)
    chain = (MESSAGES.get(loc) or {}, MESSAGES[DEFAULT_LOCALE])
    template: str | None = None
    for bucket in chain:
        raw = bucket.get(key)
        if raw is not None:
            template = raw
            break
    if template is None:
        template = key
    if kwargs:
        return template.format(**kwargs)
    return template


def state_options_for(locale: str) -> tuple[tuple[str, str], ...]:
    return tuple((k, t(locale, f"state_{k}")) for k in STATE_ORDER)


def state_previews_for(locale: str) -> dict[str, str]:
    return {k: t(locale, f"preview_{k}") for k in STATE_ORDER}


def render_state_previews_html(locale: str) -> str:
    lines = [f"<b>{t(locale, 'state_preview_heading')}</b>"]
    for key, label in state_options_for(locale):
        preview = state_previews_for(locale)[key]
        lines.append(f"{label} — {preview}")
    return "\n".join(lines)


def initial_rating_labels_for(locale: str) -> tuple[tuple[int, str], ...]:
    return tuple((i, t(locale, f"rating_{i}")) for i in range(1, 6))


def final_rating_labels_for(locale: str) -> tuple[tuple[int, str], ...]:
    return initial_rating_labels_for(locale)


def feedback_focus_options_for(locale: str) -> tuple[tuple[str, str], ...]:
    return tuple((k, t(locale, f"feedback_{k}")) for k in FEEDBACK_ORDER)


def render_initial_rating_guide(locale: str) -> str:
    return "\n".join(f"{score} — {label}" for score, label in initial_rating_labels_for(locale))


def render_final_rating_guide(locale: str) -> str:
    return render_initial_rating_guide(locale)


def reply_button_texts_for(key: str) -> frozenset[str]:
    """All locale variants for F.text.in_(...) (e.g. key='btn_start' → frozenset)."""
    return frozenset(t(loc, key) for loc in SUPPORTED_LOCALES)


BTN_START_VARIANTS = reply_button_texts_for("btn_start")
BTN_ABOUT_VARIANTS = reply_button_texts_for("btn_about")
BTN_DONATE_VARIANTS = reply_button_texts_for("btn_donate")
BTN_FEEDBACK_VARIANTS = reply_button_texts_for("btn_feedback")
BTN_ADMIN_VARIANTS = reply_button_texts_for("btn_admin")
BTN_ADMIN_RESTART_VARIANTS = reply_button_texts_for("btn_admin_restart")


def analytics_period_label(locale: str, period_key: str) -> str:
    return t(locale, f"period_{period_key}")


def release_action_label(locale: str, action: str) -> str:
    a = (action or "").strip().lower()
    return {
        "bootstrap": t(locale, "release_action_bootstrap"),
        "activate": t(locale, "release_action_activate"),
    }.get(a, action or t(locale, "dash"))
