from domain.protocol_engine import _paragraphize
from domain.protocols import build_default_protocol_engine


def test_build_default_protocol_engine_uses_expected_protocol_ids() -> None:
    engine = build_default_protocol_engine()
    assert engine.resolve_protocol_id("anxious") == "anxious"
    assert engine.resolve_protocol_id("tired") == "tired"
    assert engine.resolve_protocol_id("overwhelmed") == "overwhelmed"
    assert engine.resolve_protocol_id("low_energy") == "low_energy"
    assert engine.resolve_protocol_id("cant_sleep") == "cant_sleep"
    assert engine.resolve_protocol_id("need_inspiration") == "need_inspiration"


def test_protocol_messages_include_phase_emoji_and_index() -> None:
    engine = build_default_protocol_engine()
    step = engine.get_step("tired", 0)
    assert step is not None
    msg = engine.format_step_message(step, index=0, total=engine.step_count("tired"))
    assert "🧍" in msg
    assert "Шаг 1 из 4" in msg
    assert "<b>Шаг 1. Тело:" in msg
    assert "⏱️ <b>Время</b>" in msg
    assert "≈ 2 мин" in msg
    assert "▶️ <b>Как делать</b>" in msg
    assert "🛟 <b>Если нужен другой вариант</b>" in msg


def test_paragraphize_breaks_text_into_mobile_blocks() -> None:
    text = "Первое предложение. Второе предложение. Третье предложение."
    result = _paragraphize(text)
    assert "\n\n" in result
