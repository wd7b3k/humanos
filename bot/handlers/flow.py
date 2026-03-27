"""Сценарий протокола: FSM и колбэки (бизнес-логика в use cases)."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup

from app.session_util import load_session, save_session
from app.use_cases.context import AppContext
from app.use_cases.donation import DonationUseCase
from app.use_cases.finish_protocol import FinishProtocolUseCase
from app.use_cases.next_step import NextStepUseCase
from app.use_cases.select_state import SelectStateUseCase
from app.use_cases.start import StartUseCase
from app.use_cases.start_protocol import StartProtocolUseCase
from bot.keyboards import (
    improved_finish_keyboard,
    main_menu_reply,
    protocol_next_keyboard,
    protocol_quit_confirm_keyboard,
    rating_keyboard,
    state_selection_keyboard,
)
from bot.protocol_media import (
    phase_media,
    remember_phase_file_id,
)
from bot.reply_keyboard_strip import maybe_strip_reply_keyboard
from bot.section_media import remember_section_file_id, section_media
from bot.states import FlowStates
from bot.telegram_safe import ensure_html_message, html_message_and_caption, safe_answer_callback
from shared.constants import (
    EVENT_PROTOCOL_ABANDON_MENU,
    EVENT_PROTOCOL_NEXT_CLICKED,
    EVENT_PROTOCOL_STEP_SHOWN,
    RATING_MAX,
    RATING_MIN,
    render_final_rating_guide_locale,
)
from shared.dto import ErrorResult, FinishResult, ProtocolStartResult, ProtocolStepResult, StateSelectedResult
from shared.locale import (
    BTN_START_VARIANTS,
    t,
)

log = logging.getLogger(__name__)

_RATING_TEXT = re.compile(r"^[1-5]$")


class OneToTenRatingFilter(BaseFilter):
    """Текстовая оценка 1..5 (запасной вариант)."""

    async def __call__(self, message: Message) -> bool:
        return bool(message.text and _RATING_TEXT.match(message.text.strip()))


def _parse_rating_callback(data: str, prefix: str) -> int | None:
    if not data.startswith(f"{prefix}:"):
        return None
    try:
        n = int(data.split(":", 1)[1])
    except ValueError:
        return None
    if RATING_MIN <= n <= RATING_MAX:
        return n
    return None


def build_flow_router(ctx: AppContext) -> Router:
    router = Router(name="flow")

    start_uc = StartUseCase(ctx)
    select_uc = SelectStateUseCase(ctx)
    proto_start_uc = StartProtocolUseCase(ctx)
    next_uc = NextStepUseCase(ctx)
    finish_uc = FinishProtocolUseCase(ctx)
    donation_uc = DonationUseCase(ctx)

    def _menu_persistent() -> bool:
        return not ctx.settings.bot_hide_reply_keyboard_outside_home

    def _menu_markup(user_id: int | str, locale: str) -> ReplyKeyboardMarkup:
        return main_menu_reply(
            is_admin=ctx.settings.is_admin(user_id),
            locale=locale,
            persistent=_menu_persistent(),
        )

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
            photo_kw: dict = {
                "photo": media,
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            }
            if cap is not None:
                photo_kw["caption"] = cap
            sent = await message.answer_photo(**photo_kw)
            if not cached:
                remember_section_file_id(section_key, sent)
        except (TelegramBadRequest, TelegramNetworkError):
            log.warning("section image send failed for %s", section_key, exc_info=True)
            await message.answer(body, parse_mode="HTML", reply_markup=reply_markup)

    async def _send_protocol_step(message: Message, step: ProtocolStepResult, locale: str) -> None:
        await maybe_strip_reply_keyboard(message, ctx.settings)
        ctx.analytics.track(
            EVENT_PROTOCOL_STEP_SHOWN,
            message.from_user.id,
            {
                "protocol_id": step.protocol_id,
                "step_index": step.step_index,
                "total_steps": step.total_steps,
                "locale": locale,
            },
            app_type="telegram",
        )
        media, cached = phase_media(step.step_index)
        body, cap = html_message_and_caption(step.text, locale=locale)
        if media is None:
            await message.answer(
                body,
                parse_mode="HTML",
                reply_markup=protocol_next_keyboard(locale),
            )
            return
        try:
            photo_kw: dict = {
                "photo": media,
                "parse_mode": "HTML",
                "reply_markup": protocol_next_keyboard(locale),
            }
            if cap is not None:
                photo_kw["caption"] = cap
            sent = await message.answer_photo(**photo_kw)
            if not cached:
                remember_phase_file_id(step.step_index, sent)
        except (TelegramBadRequest, TelegramNetworkError):
            log.warning("phase image send failed, fallback to text", exc_info=True)
            await message.answer(
                body,
                parse_mode="HTML",
                reply_markup=protocol_next_keyboard(locale),
            )

    async def _launch_protocol(message: Message, state: FSMContext, locale: str) -> None:
        await state.clear()
        out = await start_uc.execute(message.from_user.id, app_type="telegram", locale=locale)
        await state.set_state(FlowStates.choosing_state)
        extra = t(locale, "flow_choose_state_title")
        # Reply-меню и inline нельзя на одном сообщении: приветствие + нижнее меню — одно;
        # выбор состояния — следующее с inline (без отдельного «·»).
        await _send_section_card(
            message,
            section_key="start_choice",
            text=out.text,
            reply_markup=_menu_markup(message.from_user.id, locale),
            locale=locale,
            strip_reply=False,
        )
        await message.answer(
            extra,
            parse_mode="HTML",
            reply_markup=state_selection_keyboard(locale),
        )

    def _share_friend_url(locale: str) -> str:
        text = t(locale, "flow_share_friend_text")
        return (
            "https://t.me/share/url"
            f"?url={quote(ctx.settings.bot_public_url, safe='')}"
            f"&text={quote(text, safe='')}"
        )

    async def _show_finish_result(
        message: Message,
        result: FinishResult,
        user_id: int | str,
        locale: str,
    ) -> None:
        if result.improved:
            full = f"{result.text}\n\n{t(locale, 'flow_finish_improved_extra')}"
            await maybe_strip_reply_keyboard(message, ctx.settings)
            await _send_section_card(
                message,
                section_key="practice_end",
                text=full,
                reply_markup=improved_finish_keyboard(
                    locale,
                    share_url=_share_friend_url(locale),
                    donation_url=donation_uc.build_redirect_url(
                        user_id,
                        "finish_improved",
                        app_type="telegram",
                    ),
                ),
                locale=locale,
                strip_reply=False,
            )
            return
        await _send_section_card(
            message,
            section_key="practice_end",
            text=result.text,
            reply_markup=_menu_markup(user_id, locale),
            locale=locale,
            strip_reply=False,
        )

    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext, locale: str) -> None:
        await _launch_protocol(message, state, locale)

    @router.message(F.text.in_(BTN_START_VARIANTS))
    async def text_start_protocol(message: Message, state: FSMContext, locale: str) -> None:
        await _launch_protocol(message, state, locale)

    @router.callback_query(F.data.startswith("state:"), FlowStates.choosing_state)
    async def on_state_chosen(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        if not query.data or not query.message:
            await safe_answer_callback(query)
            return
        await safe_answer_callback(query)
        key = query.data.split(":", 1)[1]
        result = await select_uc.execute(query.from_user.id, key, app_type="telegram", locale=locale)
        if isinstance(result, ErrorResult):
            await query.message.answer(ensure_html_message(result.message, locale=locale))
            return
        assert isinstance(result, StateSelectedResult)
        await state.set_state(FlowStates.initial_rating)
        await maybe_strip_reply_keyboard(query.message, ctx.settings)
        await query.message.answer(
            ensure_html_message(result.text, fallback=t(locale, "flow_rating_fallback"), locale=locale),
            parse_mode="HTML",
            reply_markup=rating_keyboard(locale, "ir"),
        )
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            log.warning("edit_reply_markup failed", exc_info=True)

    @router.callback_query(F.data.startswith("ir:"), FlowStates.initial_rating)
    async def on_initial_rating_cb(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        if not query.data or not query.message:
            await safe_answer_callback(query)
            return
        rating = _parse_rating_callback(query.data, "ir")
        if rating is None:
            await safe_answer_callback(query, t(locale, "callback_bad_value"), show_alert=True)
            return
        await safe_answer_callback(query)
        result = await proto_start_uc.execute(query.from_user.id, rating, app_type="telegram", locale=locale)
        if isinstance(result, ErrorResult):
            log.warning("start_protocol: %s — %s", result.code, result.message)
            await query.message.answer(ensure_html_message(result.message, locale=locale))
            return
        assert isinstance(result, ProtocolStartResult)
        await state.set_state(FlowStates.protocol_step)
        first = result.first_step
        await _send_protocol_step(query.message, first, locale)

    @router.message(FlowStates.initial_rating, OneToTenRatingFilter())
    async def on_initial_rating_text(message: Message, state: FSMContext, locale: str) -> None:
        rating = int(message.text.strip())
        result = await proto_start_uc.execute(message.from_user.id, rating, app_type="telegram", locale=locale)
        if isinstance(result, ErrorResult):
            log.warning("start_protocol: %s — %s", result.code, result.message)
            await message.answer(
                ensure_html_message(result.message, locale=locale),
                reply_markup=rating_keyboard(locale, "ir"),
            )
            return
        assert isinstance(result, ProtocolStartResult)
        await state.set_state(FlowStates.protocol_step)
        first = result.first_step
        await _send_protocol_step(message, first, locale)

    @router.callback_query(F.data == "proto:next", FlowStates.protocol_step)
    async def on_proto_next(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        if not query.message:
            await safe_answer_callback(query)
            return
        await safe_answer_callback(query)
        outcome = await next_uc.execute(query.from_user.id, locale=locale)
        if isinstance(outcome, ErrorResult):
            await query.message.answer(ensure_html_message(outcome.message, locale=locale))
            return
        if outcome.protocol_id is not None and outcome.step_index_before is not None:
            ctx.analytics.track(
                EVENT_PROTOCOL_NEXT_CLICKED,
                query.from_user.id,
                {
                    "protocol_id": outcome.protocol_id,
                    "from_step_index": outcome.step_index_before,
                    "locale": locale,
                },
                app_type="telegram",
            )
        if outcome.kind == "need_final_rating":
            await state.set_state(FlowStates.final_rating)
            await maybe_strip_reply_keyboard(query.message, ctx.settings)
            guide = render_final_rating_guide_locale(locale)
            await query.message.answer(
                t(locale, "flow_end_practice_title", guide=guide),
                parse_mode="HTML",
                reply_markup=rating_keyboard(locale, "fr"),
            )
            return
        if outcome.step:
            await _send_protocol_step(query.message, outcome.step, locale)

    @router.callback_query(F.data == "nav:quit_proto", FlowStates.protocol_step)
    async def on_quit_proto_ask(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query)
        if query.message:
            await query.message.answer(
                t(locale, "nav_quit_proto_prompt"),
                parse_mode="HTML",
                reply_markup=protocol_quit_confirm_keyboard(locale),
            )

    @router.callback_query(F.data == "nav:quit_no", FlowStates.protocol_step)
    async def on_quit_proto_no(query: CallbackQuery, locale: str) -> None:
        await safe_answer_callback(query, t(locale, "callback_quit_continue"))

    @router.callback_query(F.data == "nav:quit_yes", FlowStates.protocol_step)
    async def on_quit_proto_yes(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        await safe_answer_callback(query)
        uid = query.from_user.id
        sess = await load_session(ctx.users, uid)
        ctx.analytics.track(
            EVENT_PROTOCOL_ABANDON_MENU,
            uid,
            {
                "protocol_id": sess.protocol_id or "",
                "step_index": sess.step_index,
                "locale": locale,
            },
            app_type="telegram",
        )
        await state.clear()
        updated = sess.reset_flow()
        await save_session(ctx.users, uid, updated)
        if query.message:
            await query.message.answer(
                t(locale, "nav_home_body"),
                parse_mode="HTML",
                reply_markup=_menu_markup(uid, locale),
            )

    @router.callback_query(F.data.startswith("fr:"), FlowStates.final_rating)
    async def on_final_rating_cb(query: CallbackQuery, state: FSMContext, locale: str) -> None:
        if not query.data or not query.message:
            await safe_answer_callback(query)
            return
        rating = _parse_rating_callback(query.data, "fr")
        if rating is None:
            await safe_answer_callback(query, t(locale, "callback_bad_value"), show_alert=True)
            return
        await safe_answer_callback(query)
        result = await finish_uc.execute(query.from_user.id, rating, app_type="telegram", locale=locale)
        if isinstance(result, ErrorResult):
            await query.message.answer(
                ensure_html_message(result.message, locale=locale),
                reply_markup=rating_keyboard(locale, "fr"),
            )
            return
        await state.clear()
        assert isinstance(result, FinishResult)
        await _show_finish_result(query.message, result, query.from_user.id, locale)

    @router.message(FlowStates.final_rating, OneToTenRatingFilter())
    async def on_final_rating_text(message: Message, state: FSMContext, locale: str) -> None:
        rating = int(message.text.strip())
        result = await finish_uc.execute(message.from_user.id, rating, app_type="telegram", locale=locale)
        if isinstance(result, ErrorResult):
            await message.answer(
                ensure_html_message(result.message, locale=locale),
                reply_markup=rating_keyboard(locale, "fr"),
            )
            return
        await state.clear()
        assert isinstance(result, FinishResult)
        await _show_finish_result(message, result, message.from_user.id, locale)

    @router.message(FlowStates.initial_rating)
    async def invalid_initial_rating(message: Message, locale: str) -> None:
        await message.answer(
            t(locale, "flow_invalid_initial_rating"),
            reply_markup=rating_keyboard(locale, "ir"),
        )

    @router.message(FlowStates.final_rating)
    async def invalid_final_rating(message: Message, locale: str) -> None:
        await message.answer(
            t(locale, "flow_invalid_final_rating"),
            reply_markup=rating_keyboard(locale, "fr"),
        )

    return router
