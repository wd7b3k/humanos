"""Telegram keyboards — layout only; labels from locale catalog."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from shared.locale import (
    feedback_focus_options_for,
    final_rating_labels_for,
    initial_rating_labels_for,
    state_options_for,
    t,
)


def _chunk(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def main_menu_reply(*, is_admin: bool, locale: str, persistent: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text=t(locale, "btn_start")),
            KeyboardButton(text=t(locale, "btn_donate")),
        ],
        [
            KeyboardButton(text=t(locale, "btn_about")),
            KeyboardButton(text=t(locale, "btn_feedback")),
        ],
    ]
    if is_admin:
        keyboard.append(
            [
                KeyboardButton(text=t(locale, "btn_admin")),
                KeyboardButton(text=t(locale, "btn_admin_restart")),
            ]
        )
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=persistent,
        input_field_placeholder=t(locale, "reply_kb_placeholder"),
    )


def state_selection_keyboard(locale: str) -> InlineKeyboardMarkup:
    pairs = list(state_options_for(locale))
    rows: list[list[InlineKeyboardButton]] = []
    for row_keys in _chunk(pairs, 2):
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"state:{key}") for key, label in row_keys]
        )
    rows.append([InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_keyboard(locale: str, prefix: str) -> InlineKeyboardMarkup:
    labels = initial_rating_labels_for(locale) if prefix == "ir" else final_rating_labels_for(locale)
    row1 = [
        InlineKeyboardButton(text=label, callback_data=f"{prefix}:{score}")
        for score, label in labels[:3]
    ]
    row2 = [
        InlineKeyboardButton(text=label, callback_data=f"{prefix}:{score}")
        for score, label in labels[3:]
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row1,
            row2,
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")],
        ]
    )


def protocol_next_keyboard(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(locale, "kb_proto_next"), callback_data="proto:next"),
                InlineKeyboardButton(text=t(locale, "kb_proto_finish_home"), callback_data="nav:home"),
            ],
        ],
    )


def donation_keyboard(locale: str, *, donation_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "kb_donate_humanos"), url=donation_url)],
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")],
        ],
    )


def improved_finish_keyboard(locale: str, *, share_url: str, donation_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "kb_share_friend"), url=share_url)],
            [InlineKeyboardButton(text=t(locale, "kb_donate_humanos"), url=donation_url)],
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")],
        ]
    )


def about_root_keyboard(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "kb_about_how"), callback_data="about:how")],
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="about:close")],
        ],
    )


def about_back_keyboard(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "kb_about_back_section"), callback_data="about:root")],
        ],
    )


def admin_analytics_keyboard(locale: str, *, selected_period: str = "today") -> InlineKeyboardMarkup:
    period_buttons = (
        ("today", "kb_period_today"),
        ("yesterday", "kb_period_yesterday"),
        ("7d", "kb_period_7d"),
        ("30d", "kb_period_30d"),
    )
    rows = []
    current_row: list[InlineKeyboardButton] = []
    for key, label_key in period_buttons:
        prefix = "✅ " if key == selected_period else ""
        current_row.append(
            InlineKeyboardButton(
                text=f"{prefix}{t(locale, label_key)}",
                callback_data=f"admin:period:{key}",
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            [InlineKeyboardButton(text=t(locale, "kb_admin_refresh"), callback_data=f"admin:analytics:{selected_period}")],
            [InlineKeyboardButton(text=t(locale, "kb_admin_releases"), callback_data="admin:releases")],
            [InlineKeyboardButton(text=t(locale, "kb_admin_feedback_msgs"), callback_data=f"admin:feedback:{selected_period}")],
            [InlineKeyboardButton(text=t(locale, "kb_admin_recent"), callback_data=f"admin:recent:{selected_period}")],
            [InlineKeyboardButton(text=t(locale, "kb_admin_restart_bot"), callback_data="admin:restart")],
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")],
        ],
    )


def feedback_root_keyboard(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "kb_feedback_survey"), callback_data="feedback:survey")],
            [InlineKeyboardButton(text=t(locale, "kb_feedback_write"), callback_data="feedback:message")],
            [InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")],
        ],
    )


def feedback_survey_keyboard(locale: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"feedback:topic:{key}")]
        for key, label in feedback_focus_options_for(locale)
    ]
    rows.append([InlineKeyboardButton(text=t(locale, "kb_feedback_back"), callback_data="feedback:root")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_release_archive_keyboard(locale: str, entries: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for release_id, label in entries:
        safe = label if len(label) <= 64 else label[:61] + "…"
        rows.append([InlineKeyboardButton(text=safe, callback_data=f"admin:release:view:{release_id}")])
    rows.append(
        [InlineKeyboardButton(text=t(locale, "kb_release_back_analytics"), callback_data="admin:analytics:today")]
    )
    rows.append([InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_release_detail_keyboard(locale: str, *, release_id: str, active: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if not active:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(locale, "kb_release_activate"),
                    callback_data=f"admin:release:activate:{release_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(locale, "kb_release_back_list"), callback_data="admin:releases")])
    rows.append([InlineKeyboardButton(text=t(locale, "kb_nav_home"), callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
