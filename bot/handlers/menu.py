"""Общее меню, раздел «О сервисе», навигация."""

from __future__ import annotations

import asyncio
import json
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from aiogram.utils.text_decorations import html_decoration as hd

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from app.use_cases.donation import DonationUseCase
from app.use_cases.preferences import PreferencesUseCase
from bot.keyboards import (
    about_back_keyboard,
    about_root_keyboard,
    admin_analytics_keyboard,
    admin_release_archive_keyboard,
    admin_release_detail_keyboard,
    donation_keyboard,
    feedback_root_keyboard,
    feedback_survey_keyboard,
    main_menu_reply,
    protocol_quit_confirm_keyboard,
)
from bot.reply_keyboard_strip import maybe_strip_reply_keyboard
from bot.section_media import remember_section_file_id, section_media
from bot.states import FlowStates
from bot.telegram_safe import ensure_html_message, html_message_and_caption, safe_answer_callback
from infrastructure.analytics import ANALYTICS_PERIODS
from shared.constants import EVENT_DONATION_SHOWN
from shared.dto import ErrorResult
from shared.locale import (
    BTN_ABOUT_VARIANTS,
    BTN_ADMIN_RESTART_VARIANTS,
    BTN_ADMIN_VARIANTS,
    BTN_DONATE_VARIANTS,
    BTN_FEEDBACK_VARIANTS,
    analytics_period_label,
    feedback_focus_options_for,
    release_action_label,
    t,
)

log = logging.getLogger(__name__)


def _format_iso_ts(raw: str, locale: str) -> str:
    if not raw or not str(raw).strip():
        return t(locale, "dash")
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(s)
        return dt.strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        return str(raw)[:19]


def build_menu_router(ctx: AppContext) -> Router:
    router = Router(name="menu")
    donation_uc = DonationUseCase(ctx)
    prefs_uc = PreferencesUseCase(ctx)

    def _menu_persistent() -> bool:
        return not ctx.settings.bot_hide_reply_keyboard_outside_home

    def _menu_markup(user_id: int | str, locale: str):
        return main_menu_reply(
            is_admin=ctx.settings.is_admin(user_id),
            locale=locale,
            persistent=_menu_persistent(),
        )

    def _format_incident_status(locale: str) -> str:
        status = ctx.incidents.snapshot()
        if status.active:
            return t(
                locale,
                "incident_active",
                reason=hd.quote(status.last_problem_reason or t(locale, "unknown")),
                when=hd.quote(status.last_problem_at or t(locale, "unknown")),
                restarts=status.restart_count,
            )
        resolved = status.last_resolved_at or t(locale, "dash")
        return t(
            locale,
            "incident_ok",
            resolved=hd.quote(resolved),
            restarts=status.restart_count,
        )

    def _normalize_period(period_key: str | None) -> str:
        if period_key in ANALYTICS_PERIODS:
            return str(period_key)
        return "today"

    def _format_analytics_text(period_key: str, locale: str) -> str:
        product, internal = ctx.analytics.product_and_internal_summaries(
            period_key=period_key, recent_limit=5, locale=locale
        )

        def _segment_lines(summary, loc: str) -> tuple[str, str, str, str]:
            state_counts = summary.state_counts or {}
            top_states = (
                "\n".join(f"• {hd.quote(state)} — <b>{count}</b>" for state, count in state_counts.items())
                if state_counts
                else t(loc, "analytics_segment_empty")
            )
            feedback_labels = dict(feedback_focus_options_for(loc))
            feedback_counts = summary.feedback_topic_counts or {}
            feedback_segments = (
                "\n".join(
                    f"• {hd.quote(feedback_labels.get(topic, topic))} — <b>{count}</b>"
                    for topic, count in feedback_counts.items()
                )
                if feedback_counts
                else t(loc, "analytics_segment_empty")
            )
            app_type_counts = summary.app_type_counts or {}
            app_type_segments = (
                "\n".join(f"• {hd.quote(app_type)} — <b>{count}</b>" for app_type, count in app_type_counts.items())
                if app_type_counts
                else t(loc, "analytics_segment_empty")
            )
            return top_states, feedback_segments, app_type_segments, str(summary.total_events)

        p_states, p_feedback, p_apps, p_total = _segment_lines(product, locale)
        i_states, i_feedback, i_apps, i_total = _segment_lines(internal, locale)

        hint = ""
        if product.total_events == 0 and internal.total_events > 0:
            hint = t(locale, "analytics_hint_internal_only")

        product_block = t(
            locale,
            "analytics_product_block",
            p_total=p_total,
            starts=product.event_counts.get("start", 0),
            state_sel=product.event_counts.get("state_selected", 0),
            started=product.started_protocols,
            completed=product.completed_protocols,
            improved=product.improved_count,
            don_shown=product.donation_shown_count,
            don_click=product.donation_clicks,
            active=product.active_users,
            returning=product.returning_users,
            newu=product.new_users_in_period,
            multiday=product.multi_day_active_users,
            repeat_start=product.repeat_start_users,
            p_apps=p_apps,
            p_states=p_states,
            p_feedback=p_feedback,
            fb_msg=product.feedback_messages,
        )

        internal_block = t(
            locale,
            "analytics_internal_block",
            i_total=i_total,
            istart=internal.event_counts.get("start", 0),
            istartp=internal.started_protocols,
            icompl=internal.completed_protocols,
            idsh=internal.donation_shown_count,
            idcl=internal.donation_clicks,
            iact=internal.active_users,
            iret=internal.returning_users,
            imulti=internal.multi_day_active_users,
            i_apps=i_apps,
            i_states=i_states,
            i_feedback=i_feedback,
        )

        return (
            f"<b>{t(locale, 'analytics_title')}</b>\n\n"
            f"<b>{t(locale, 'analytics_period_label')}</b>: {hd.quote(product.period_label)}\n\n"
            f"{hint}"
            f"{product_block}\n\n"
            f"{internal_block}\n\n"
            f"{_format_incident_status(locale)}"
        )

    def _format_recent_events(period_key: str, locale: str) -> str:
        summary = ctx.analytics.summary(period_key=period_key, recent_limit=10, audience="all", locale=locale)
        recent = summary.recent_events
        if not recent:
            return (
                f"<b>{t(locale, 'analytics_recent_title')}</b>\n\n"
                f"{t(locale, 'analytics_period_label')}: {summary.period_label}\n\n"
                f"{t(locale, 'analytics_recent_empty')}"
            )
        lines = [
            f"<b>{t(locale, 'analytics_recent_title')}</b>\n\n"
            f"{t(locale, 'analytics_period_label')}: {summary.period_label}"
        ]
        for event in reversed(recent):
            app_type = str(event.payload.get("app_type") or t(locale, "unknown"))
            payload = ", ".join(f"{k}={v}" for k, v in event.payload.items()) or t(
                locale, "analytics_recent_no_payload"
            )
            lines.append(
                f"• <b>{hd.quote(event.name)}</b> | app={hd.quote(app_type)} | user={hd.quote(event.user_id)} | "
                f"{hd.quote(payload)}"
            )
        return "\n".join(lines)

    async def _format_feedback_messages(period_key: str, locale: str) -> str:
        period = _normalize_period(period_key)
        entries = await ctx.feedback_store.recent(period_key=period, limit=10)
        title = analytics_period_label(locale, period)
        if not entries:
            return (
                f"<b>{t(locale, 'analytics_feedback_title')}</b>\n\n"
                f"{t(locale, 'analytics_period_label')}: {title}\n\n"
                f"{t(locale, 'analytics_recent_empty')}"
            )
        lines = [f"<b>{t(locale, 'analytics_feedback_title')}</b>\n\n{t(locale, 'analytics_period_label')}: {title}"]
        for entry in entries:
            username = f"@{entry.username}" if entry.username else t(locale, "dash")
            lines.append(
                "\n".join(
                    [
                        f"• <b>{hd.quote(entry.full_name or t(locale, 'no_name'))}</b>",
                        f"user={hd.quote(entry.user_id)} | username={hd.quote(username)}",
                        f"<i>{hd.quote(entry.ts)}</i>",
                        hd.quote(entry.text),
                    ]
                )
            )
        return "\n\n".join(lines)

    def _format_release_archive_text(locale: str) -> str:
        releases = ctx.release_store.list_releases()
        if not releases:
            return t(locale, "release_archive_empty")
        lines = [t(locale, "release_archive_intro").rstrip()]
        active = next((item for item in releases if item.active), None)
        if active:
            lines.append(
                t(
                    locale,
                    "release_active_line",
                    version=hd.quote(active.version),
                    title=hd.quote(active.title),
                )
            )
        lines.append(t(locale, "release_list_heading"))
        for item in releases:
            status = t(locale, "release_status_active") if item.active else t(locale, "release_status_archive")
            created = _format_iso_ts(item.created_at, locale)
            lines.append(
                f"• <b>{hd.quote(item.version)}</b> · {hd.quote(status)} · {hd.quote(created)}\n"
                f"  {hd.quote(item.title)}"
            )
        events = ctx.release_store.recent_events(limit=8)
        if events:
            lines.append("")
            lines.append(t(locale, "release_journal_title"))
            lines.append(t(locale, "release_journal_note"))
            for event in events:
                action_loc = release_action_label(locale, event.action)
                ts_fmt = _format_iso_ts(event.ts, locale)
                actor_loc = (
                    t(locale, "release_actor_system")
                    if event.actor == "system"
                    else t(locale, "release_actor_id", actor=hd.quote(event.actor))
                )
                lines.append(
                    f"• {hd.quote(ts_fmt)} · {hd.quote(action_loc)} · "
                    f"v{hd.quote(event.version)} · {actor_loc}"
                )
                if (event.note or "").strip():
                    lines.append(f"  └ {hd.quote(event.note)}")
        return "\n".join(lines)

    def _format_release_detail_text(release_id: str, locale: str) -> tuple[str, bool]:
        releases = {item.release_id: item for item in ctx.release_store.list_releases()}
        item = releases.get(release_id)
        if item is None:
            return t(locale, "release_detail_not_found"), False
        try:
            raw = ctx.release_store.get_release_data(release_id)
        except (OSError, json.JSONDecodeError, KeyError):
            raw = {}
        protocols = raw.get("protocols") or {}
        proto_lines: list[str] = []
        for pid in sorted(protocols.keys()):
            spec = protocols[pid]
            sl = str(spec.get("state_label") or pid)
            tl = str(spec.get("title") or "")
            proto_lines.append(f"• <b>{hd.quote(sl)}</b> ({hd.quote(pid)}) — {hd.quote(tl)}")
        if proto_lines:
            proto_section = t(locale, "release_detail_protocols", count=len(proto_lines), lines="\n".join(proto_lines))
        else:
            proto_section = t(locale, "release_detail_protocols_empty")
        if item.notes:
            notes = "\n".join(f"{i}. {hd.quote(n)}" for i, n in enumerate(item.notes, 1))
        else:
            notes = t(locale, "release_detail_notes_empty")
        notes_block = t(locale, "release_detail_notes_heading", notes=notes)
        status = (
            t(locale, "release_detail_status_active")
            if item.active
            else t(locale, "release_detail_status_archive")
        )
        created = _format_iso_ts(item.created_at, locale)
        text = t(
            locale,
            "release_detail_card",
            rid=hd.quote(item.release_id),
            version=hd.quote(item.version),
            status=status,
            created=hd.quote(created),
            title=hd.quote(item.title),
            proto=proto_section,
            notes_block=notes_block,
        )
        return text, item.active

    async def _show_admin_analytics(message: Message, *, locale: str, period_key: str = "today") -> None:
        period = _normalize_period(period_key)
        await maybe_strip_reply_keyboard(message, ctx.settings)
        await message.answer(
            _format_analytics_text(period, locale),
            parse_mode="HTML",
            reply_markup=admin_analytics_keyboard(locale, selected_period=period),
        )

    async def _show_donation_entry(message: Message, *, locale: str, source: str) -> None:
        release_meta = ctx.protocols.current_release()
        ctx.analytics.track(
            EVENT_DONATION_SHOWN,
            message.from_user.id,
            {
                "source": source,
                "release_id": str(release_meta["release_id"]),
                "release_version": str(release_meta["release_version"]),
                "variant_id": None,
                "locale": locale,
            },
            app_type="telegram",
        )
        await maybe_strip_reply_keyboard(message, ctx.settings)
        await _send_section_card(
            message,
            section_key="donate",
            text=t(locale, "donate_card"),
            reply_markup=donation_keyboard(
                locale,
                donation_url=donation_uc.build_redirect_url(message.from_user.id, source, app_type="telegram"),
            ),
            locale=locale,
            strip_reply=False,
        )

    async def _show_feedback_root(message: Message, *, locale: str) -> None:
        await maybe_strip_reply_keyboard(message, ctx.settings)
        await _send_section_card(
            message,
            section_key="feedback",
            text=t(locale, "feedback_root"),
            reply_markup=feedback_root_keyboard(locale),
            locale=locale,
            strip_reply=False,
        )

    def _topic_label(topic_key: str, locale: str) -> str:
        mapping = dict(feedback_focus_options_for(locale))
        return mapping.get(topic_key, topic_key)

    async def _forward_feedback_to_admins(
        *,
        bot,
        user_id: int,
        username: str | None,
        full_name: str | None,
        title: str,
        body_html: str,
        locale: str,
    ) -> None:
        admin_targets = sorted(ctx.settings.admin_ids)
        if not admin_targets:
            return
        safe_username = f"@{username}" if username else t(locale, "dash")
        text = t(
            locale,
            "feedback_forward_admin_template",
            title=title,
            user_id=user_id,
            username=hd.quote(safe_username),
            full_name=hd.quote(full_name or t(locale, "dash")),
            body=body_html,
        )
        for admin_id in admin_targets:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                log.exception("feedback forward failed for admin %s", admin_id)

    async def _send_section_card(
        message: Message,
        *,
        section_key: str,
        text: str,
        reply_markup=None,
        locale: str,
        strip_reply: bool = False,
    ) -> None:
        if strip_reply:
            await maybe_strip_reply_keyboard(message, ctx.settings)
        media, cached = section_media(section_key)
        body, cap = html_message_and_caption(text, locale=locale)
        if media is None:
            await message.answer(body, parse_mode="HTML", reply_markup=reply_markup)
            return
        try:
            photo_kw: dict = {"photo": media, "parse_mode": "HTML", "reply_markup": reply_markup}
            if cap is not None:
                photo_kw["caption"] = cap
            sent = await message.answer_photo(**photo_kw)
            if not cached:
                remember_section_file_id(section_key, sent)
        except (TelegramBadRequest, TelegramNetworkError):
            log.warning("section image send failed for %s", section_key, exc_info=True)
            await message.answer(body, parse_mode="HTML", reply_markup=reply_markup)

    async def _edit_section_card(
        query: CallbackQuery,
        *,
        section_key: str,
        text: str,
        reply_markup=None,
        locale: str,
    ) -> None:
        if not query.message:
            return
        media, cached = section_media(section_key)
        body, cap = html_message_and_caption(text, locale=locale)
        if media is None:
            try:
                await query.message.edit_text(body, parse_mode="HTML", reply_markup=reply_markup)
            except TelegramBadRequest as exc:
                if "message is not modified" in str(exc).lower():
                    return
                raise
            return
        try:
            media_obj = (
                InputMediaPhoto(media=media, caption=cap, parse_mode="HTML")
                if cap is not None
                else InputMediaPhoto(media=media)
            )
            edited = await query.message.edit_media(
                media=media_obj,
                reply_markup=reply_markup,
            )
            if not cached and isinstance(edited, Message):
                remember_section_file_id(section_key, edited)
        except (TelegramBadRequest, TelegramNetworkError) as exc:
            raw_l = str(exc).lower()
            if "message is not modified" in raw_l:
                return
            log.warning("section image edit failed for %s", section_key, exc_info=True)
            await query.message.answer(body, parse_mode="HTML", reply_markup=reply_markup)

    async def _schedule_service_restart() -> None:
        try:
            await asyncio.create_subprocess_exec(
                "/bin/bash",
                "-lc",
                "sleep 1 && systemctl restart humanos-bot.service",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            log.exception("service restart scheduling failed")
            raise

    @router.message(Command("menu"))
    async def cmd_menu(message: Message, locale: str) -> None:
        await message.answer(
            f"<b>{t(locale, 'menu_main_title')}</b>\n\n{t(locale, 'menu_main_hint')}",
            parse_mode="HTML",
            reply_markup=_menu_markup(message.from_user.id, locale),
        )

    @router.message(Command("about"))
    async def cmd_about(message: Message, locale: str) -> None:
        await maybe_strip_reply_keyboard(message, ctx.settings)
        await _send_section_card(
            message,
            section_key="about_intro",
            text=t(locale, "about_intro"),
            reply_markup=about_root_keyboard(locale),
            locale=locale,
            strip_reply=False,
        )

    @router.message(Command("feedback"))
    async def cmd_feedback(message: Message, locale: str) -> None:
        await _show_feedback_root(message, locale=locale)

    @router.message(Command("donate"))
    async def cmd_donate(message: Message, locale: str) -> None:
        await _show_donation_entry(message, locale=locale, source="donate_command")

    @router.message(Command("admin"))
    async def cmd_admin(message: Message, locale: str) -> None:
        if not ctx.settings.is_admin(message.from_user.id):
            await message.answer(t(locale, "admin_only"))
            return
        await _show_admin_analytics(message, locale=locale, period_key="today")

    @router.message(F.text.in_(BTN_ABOUT_VARIANTS))
    async def reply_about(message: Message, locale: str) -> None:
        await maybe_strip_reply_keyboard(message, ctx.settings)
        await _send_section_card(
            message,
            section_key="about_intro",
            text=t(locale, "about_intro"),
            reply_markup=about_root_keyboard(locale),
            locale=locale,
            strip_reply=False,
        )

    @router.message(F.text.in_(BTN_DONATE_VARIANTS))
    async def reply_donate(message: Message, locale: str) -> None:
        await _show_donation_entry(message, locale=locale, source="donate_menu")

    @router.message(F.text.in_(BTN_FEEDBACK_VARIANTS))
    async def reply_feedback(message: Message, locale: str) -> None:
        await _show_feedback_root(message, locale=locale)

    @router.message(F.text.in_(BTN_ADMIN_VARIANTS))
    async def reply_admin(message: Message, locale: str) -> None:
        if not ctx.settings.is_admin(message.from_user.id):
            await message.answer(t(locale, "admin_only"))
            return
        await _show_admin_analytics(message, locale=locale, period_key="today")

    @router.message(F.text.in_(BTN_ADMIN_RESTART_VARIANTS))
    async def reply_admin_restart(message: Message, locale: str) -> None:
        if not ctx.settings.is_admin(message.from_user.id):
            await message.answer(t(locale, "admin_only"))
            return
        await message.answer(t(locale, "restart_scheduled"))
        await _schedule_service_restart()

    @router.callback_query(F.data == "about:root")
    async def cb_about_root(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query)
        await _edit_section_card(
            query,
            section_key="about_intro",
            text=t(locale, "about_intro"),
            reply_markup=about_root_keyboard(locale),
            locale=locale,
        )

    @router.callback_query(F.data == "about:how")
    async def cb_about_how(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query)
        await _edit_section_card(
            query,
            section_key="about_how",
            text=t(locale, "about_how"),
            reply_markup=about_back_keyboard(locale),
            locale=locale,
        )

    @router.callback_query(F.data == "about:close")
    async def cb_about_close(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query)
        if query.message:
            try:
                await query.message.edit_reply_markup(reply_markup=None)
            except Exception:
                log.debug("about close edit failed", exc_info=True)
            await query.message.answer(
                t(locale, "about_close_body"),
                reply_markup=_menu_markup(query.from_user.id, locale),
            )

    @router.callback_query(F.data == "feedback:root")
    async def cb_feedback_root(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        await safe_answer_callback(query)
        await state.clear()
        await _edit_section_card(
            query,
            section_key="feedback",
            text=t(locale, "feedback_root_edit"),
            reply_markup=feedback_root_keyboard(locale),
            locale=locale,
        )

    @router.callback_query(F.data == "feedback:survey")
    async def cb_feedback_survey(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query)
        await _edit_section_card(
            query,
            section_key="feedback",
            text=t(locale, "feedback_survey_title"),
            reply_markup=feedback_survey_keyboard(locale),
            locale=locale,
        )

    @router.callback_query(F.data.startswith("feedback:topic:"))
    async def cb_feedback_topic(query: CallbackQuery, locale: str) -> None:
        if not query.data:
            await safe_answer_callback(query)
            return
        topic_key = query.data.rsplit(":", 1)[-1]
        result = await prefs_uc.add_feedback_topic(query.from_user.id, topic_key, locale=locale)
        if isinstance(result, ErrorResult):
            alert = ensure_html_message(
                result.message,
                fallback=t(locale, "prefs_save_failed"),
                locale=locale,
            )
            await safe_answer_callback(query, alert[:200], show_alert=True)
            return
        await safe_answer_callback(query, t(locale, "callback_saved"))
        if query.message:
            label = _topic_label(topic_key, locale)
            await query.message.answer(
                t(locale, "feedback_thanks_topic", label=label),
                parse_mode="HTML",
                reply_markup=feedback_root_keyboard(locale),
            )
            await _forward_feedback_to_admins(
                bot=query.message.bot,
                user_id=query.from_user.id,
                username=query.from_user.username,
                full_name=query.from_user.full_name,
                title=t(locale, "feedback_forward_survey_title"),
                body_html=t(locale, "feedback_forward_survey_body", label=hd.quote(label)),
                locale=locale,
            )

    @router.callback_query(F.data == "feedback:message")
    async def cb_feedback_message(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        await safe_answer_callback(query, t(locale, "callback_write_ok"))
        await state.set_state(FlowStates.feedback_message)
        if query.message:
            await query.message.answer(
                t(locale, "feedback_write_prompt"),
                parse_mode="HTML",
                reply_markup=_menu_markup(query.from_user.id, locale),
            )

    @router.callback_query(F.data == "nav:home")
    async def cb_nav_home(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        cur = await state.get_state()
        if cur == FlowStates.protocol_step.state:
            await safe_answer_callback(query)
            if query.message:
                await query.message.answer(
                    t(locale, "nav_quit_proto_prompt"),
                    parse_mode="HTML",
                    reply_markup=protocol_quit_confirm_keyboard(locale),
                )
            return
        await safe_answer_callback(query, t(locale, "callback_nav_home"))
        await state.clear()
        current = await load_session(ctx.users, query.from_user.id)
        await save_session(ctx.users, query.from_user.id, current.reset_flow())
        if query.message:
            await query.message.answer(
                t(locale, "nav_home_body"),
                parse_mode="HTML",
                reply_markup=_menu_markup(query.from_user.id, locale),
            )

    @router.callback_query(F.data.startswith("admin:analytics:"))
    async def cb_admin_analytics(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        period = _normalize_period(query.data.rsplit(":", 1)[-1] if query.data else None)
        await safe_answer_callback(query, t(locale, "callback_refresh"))
        if query.message:
            try:
                await query.message.edit_text(
                    ensure_html_message(_format_analytics_text(period, locale), locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_analytics_keyboard(locale, selected_period=period),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data.startswith("admin:recent:"))
    async def cb_admin_recent(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        period = _normalize_period(query.data.rsplit(":", 1)[-1] if query.data else None)
        await safe_answer_callback(query, t(locale, "callback_show_events"))
        if query.message:
            try:
                await query.message.edit_text(
                    ensure_html_message(_format_recent_events(period, locale), locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_analytics_keyboard(locale, selected_period=period),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data.startswith("admin:feedback:"))
    async def cb_admin_feedback(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        period = _normalize_period(query.data.rsplit(":", 1)[-1] if query.data else None)
        await safe_answer_callback(query, t(locale, "callback_show_fb"))
        if query.message:
            try:
                await query.message.edit_text(
                    ensure_html_message(await _format_feedback_messages(period, locale), locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_analytics_keyboard(locale, selected_period=period),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data == "admin:releases")
    async def cb_admin_releases(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        await safe_answer_callback(query, t(locale, "callback_open_releases"))
        if query.message:
            rel_list = ctx.release_store.list_releases()
            kb_entries: list[tuple[str, str]] = []
            for item in rel_list:
                prefix = "✅ " if item.active else "📦 "
                label = f"{prefix}{item.version}"
                if len(label) > 64:
                    label = prefix + item.version[: max(0, 64 - len(prefix) - 1)] + "…"
                kb_entries.append((item.release_id, label))
            try:
                await query.message.edit_text(
                    ensure_html_message(_format_release_archive_text(locale), locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_release_archive_keyboard(locale, kb_entries),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data.startswith("admin:release:view:"))
    async def cb_admin_release_view(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        release_id = query.data.rsplit(":", 1)[-1] if query.data else ""
        await safe_answer_callback(query, t(locale, "callback_release_card"))
        if query.message:
            text, active = _format_release_detail_text(release_id, locale)
            try:
                await query.message.edit_text(
                    ensure_html_message(text, locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_release_detail_keyboard(locale, release_id=release_id, active=active),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data.startswith("admin:release:activate:"))
    async def cb_admin_release_activate(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        release_id = query.data.rsplit(":", 1)[-1] if query.data else ""
        try:
            record = ctx.release_store.activate_release(
                release_id,
                actor=str(query.from_user.id),
                note="Переключение активного релиза из Telegram-админки",
            )
        except KeyError:
            await safe_answer_callback(query, t(locale, "release_not_found"), show_alert=True)
            return
        await safe_answer_callback(query, t(locale, "callback_switch_release"))
        if query.message:
            await query.message.answer(
                t(locale, "release_activate_done", version=hd.quote(record.version)),
                parse_mode="HTML",
            )
        await _schedule_service_restart()

    @router.callback_query(F.data.startswith("admin:period:"))
    async def cb_admin_period(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        period = _normalize_period(query.data.rsplit(":", 1)[-1] if query.data else None)
        await safe_answer_callback(query, t(locale, "period_ok"))
        if query.message:
            try:
                await query.message.edit_text(
                    ensure_html_message(_format_analytics_text(period, locale), locale=locale),
                    parse_mode="HTML",
                    reply_markup=admin_analytics_keyboard(locale, selected_period=period),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise

    @router.callback_query(F.data == "admin:restart")
    async def cb_admin_restart(query: CallbackQuery, locale: str) -> None:
        if not ctx.settings.is_admin(query.from_user.id):
            await safe_answer_callback(query, t(locale, "callback_no_rights"), show_alert=True)
            return
        await safe_answer_callback(query, t(locale, "callback_restarting"))
        if query.message:
            await query.message.answer(t(locale, "restart_scheduled"))
        await _schedule_service_restart()

    @router.message(FlowStates.feedback_message)
    async def on_feedback_message(message: Message, state: FSMContext, locale: str) -> None:
        result = await prefs_uc.save_feedback_message(
            message.from_user.id,
            message.text or "",
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            app_type="telegram",
            locale=locale,
        )
        if isinstance(result, ErrorResult):
            await message.answer(
                ensure_html_message(
                    result.message,
                    fallback=t(locale, "prefs_message_failed"),
                    locale=locale,
                )
            )
            return
        await state.clear()
        await _forward_feedback_to_admins(
            bot=message.bot,
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            title=t(locale, "feedback_forward_free_title"),
            body_html=hd.quote(result),
            locale=locale,
        )
        await message.answer(
            t(locale, "feedback_thanks_saved"),
            reply_markup=_menu_markup(message.from_user.id, locale),
        )

    return router
