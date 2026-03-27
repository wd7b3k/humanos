import pytest

from app.session_util import load_session
from app.use_cases.donation import DonationUseCase
from app.use_cases.finish_protocol import FinishProtocolUseCase
from app.use_cases.identity import IdentityCaptureUseCase
from app.use_cases.next_step import NextStepUseCase
from app.use_cases.preferences import PreferencesUseCase
from app.use_cases.select_state import SelectStateUseCase
from app.use_cases.start import StartUseCase
from app.use_cases.start_protocol import StartProtocolUseCase
from shared.dto import ErrorResult


@pytest.mark.asyncio()
async def test_start_use_case_resets_session_and_returns_state_options(ctx) -> None:
    out = await StartUseCase(ctx).execute("u1")
    assert "HumanOS" in out.text
    assert len(out.state_labels) == 6


@pytest.mark.asyncio()
async def test_protocol_happy_path_and_finish_improved(ctx) -> None:
    await StartUseCase(ctx).execute("u1")
    selected = await SelectStateUseCase(ctx).execute("u1", "tired")
    assert not isinstance(selected, ErrorResult)

    started = await StartProtocolUseCase(ctx).execute("u1", 4)
    assert not isinstance(started, ErrorResult)
    assert started.first_step.step_index == 0
    session = await load_session(ctx.users, "u1")
    assert session.protocol_variant_id == "main"
    assert session.protocol_release_id is not None

    nxt = await NextStepUseCase(ctx).execute("u1")
    assert not isinstance(nxt, ErrorResult)
    assert nxt.kind == "step"

    nxt = await NextStepUseCase(ctx).execute("u1")
    assert nxt.kind == "step"
    nxt = await NextStepUseCase(ctx).execute("u1")
    assert nxt.kind == "step"
    nxt = await NextStepUseCase(ctx).execute("u1")
    assert nxt.kind == "need_final_rating"

    finish = await FinishProtocolUseCase(ctx).execute("u1", 2)
    assert not isinstance(finish, ErrorResult)
    assert finish.improved is True
    assert finish.tribute_url == ctx.settings.tribute_url


@pytest.mark.asyncio()
async def test_invalid_state_and_rating_errors(ctx) -> None:
    bad_state = await SelectStateUseCase(ctx).execute("u2", "unknown")
    assert isinstance(bad_state, ErrorResult)
    assert bad_state.code == "unknown_state"

    bad_start = await StartProtocolUseCase(ctx).execute("u2", 0)
    assert isinstance(bad_start, ErrorResult)
    assert bad_start.code == "invalid_rating"


@pytest.mark.asyncio()
async def test_donation_use_case_returns_tribute_url(ctx) -> None:
    uc = DonationUseCase(ctx)
    out = await uc.execute("u3", "donate_menu")
    redirect_url = uc.build_redirect_url("u3", "donate_menu")
    assert out.url == ctx.settings.tribute_url
    assert out.source == "donate_menu"
    assert redirect_url.startswith(ctx.settings.tribute_url) or "/r/donate?" in redirect_url


@pytest.mark.asyncio()
async def test_preferences_use_case_persists_push_and_feedback(ctx) -> None:
    prefs = PreferencesUseCase(ctx)

    await prefs.set_push_permission("u4", allowed=True)
    topics = await prefs.add_feedback_topic("u4", "nutrition")
    assert not isinstance(topics, ErrorResult)
    message = await prefs.save_feedback_message(
        "u4",
        "Хочу больше практик для вечера",
        username="nightowl",
        full_name="Evening User",
    )
    assert not isinstance(message, ErrorResult)

    session = await ctx.users.get("u4")
    feedback_messages = await ctx.feedback_store.recent(period_key="today", limit=5)
    assert session["push_permission_telegram"] is True
    assert session["feedback_topics"] == ["nutrition"]
    assert feedback_messages[0].text == "Хочу больше практик для вечера"
    assert feedback_messages[0].username == "nightowl"


@pytest.mark.asyncio()
async def test_identity_capture_persists_internal_and_public_telegram_ids(ctx) -> None:
    await IdentityCaptureUseCase(ctx).sync_telegram_identity(
        user_id=12345,
        username="humanuser",
        full_name="Human User",
        language_code="ru",
    )
    session = await ctx.users.get(12345)
    assert session["telegram_internal_id"] == "12345"
    assert session["telegram_public_id"] == "humanuser"
    assert session["telegram_profile_url"] == "https://t.me/humanuser"
    assert session["client_id"]
    client = await ctx.clients.get_client(session["client_id"])
    assert client is not None
    assert client.role == "client"
