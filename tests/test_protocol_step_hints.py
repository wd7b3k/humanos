from shared.protocol_step_hints import append_protocol_rating_hints


def test_hints_single_step_only_then_rating() -> None:
    body = "step text"
    out = append_protocol_rating_hints(body, locale="ru", step_index=0, total=1)
    assert "step text" in out
    assert "шкале" in out.lower() or "1–5" in out


def test_hints_penultimate_and_last() -> None:
    base = "x"
    mid = append_protocol_rating_hints(base, locale="en", step_index=2, total=4)
    assert "one more" in mid.lower()
    last = append_protocol_rating_hints(base, locale="en", step_index=3, total=4)
    assert "next step" in last.lower() or "rating" in last.lower()


def test_hints_no_extra_for_early_steps() -> None:
    base = "early"
    out = append_protocol_rating_hints(base, locale="ru", step_index=0, total=5)
    assert out == base
