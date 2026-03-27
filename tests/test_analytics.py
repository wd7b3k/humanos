from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from shared.constants import EVENT_BOT_INTERACTION

from infrastructure.analytics import Analytics, AnalyticsEvent


def test_analytics_summary_filters_by_period() -> None:
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001 - acceptable in focused unit test
        [
            AnalyticsEvent(
                name="start",
                user_id="u1",
                payload={},
                ts="2026-03-25T10:00:00+00:00",
            ),
            AnalyticsEvent(
                name="state_selected",
                user_id="u1",
                payload={"state": "tired"},
                ts="2026-03-24T12:00:00+00:00",
            ),
            AnalyticsEvent(
                name="protocol_started",
                user_id="u2",
                payload={},
                ts="2026-03-20T12:00:00+00:00",
            ),
            AnalyticsEvent(
                name="protocol_completed",
                user_id="u3",
                payload={},
                ts="2026-03-05T12:00:00+00:00",
            ),
        ]
    )

    now = datetime(2026, 3, 25, 15, 0, tzinfo=UTC)

    today = analytics.summary(period_key="today", now=now)
    assert today.total_events == 1
    assert today.event_counts["start"] == 1

    yesterday = analytics.summary(period_key="yesterday", now=now)
    assert yesterday.total_events == 1
    assert yesterday.state_counts["tired"] == 1

    last_week = analytics.summary(period_key="7d", now=now)
    assert last_week.total_events == 3
    assert last_week.started_protocols == 1

    last_month = analytics.summary(period_key="30d", now=now)
    assert last_month.total_events == 4
    assert last_month.completed_protocols == 1


def test_analytics_summary_segments_feedback_topics_by_unique_users() -> None:
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001 - acceptable in focused unit test
        [
            AnalyticsEvent(
                name="feedback_topic_selected",
                user_id="u1",
                payload={"topic": "nutrition"},
                ts="2026-03-25T10:00:00+00:00",
            ),
            AnalyticsEvent(
                name="feedback_topic_selected",
                user_id="u1",
                payload={"topic": "nutrition"},
                ts="2026-03-25T10:05:00+00:00",
            ),
            AnalyticsEvent(
                name="feedback_topic_selected",
                user_id="u2",
                payload={"topic": "nutrition"},
                ts="2026-03-25T10:10:00+00:00",
            ),
            AnalyticsEvent(
                name="feedback_topic_selected",
                user_id="u3",
                payload={"topic": "mental"},
                ts="2026-03-25T11:00:00+00:00",
            ),
            AnalyticsEvent(
                name="feedback_message_sent",
                user_id="u3",
                payload={"length": 42},
                ts="2026-03-25T11:05:00+00:00",
            ),
        ]
    )

    now = datetime(2026, 3, 25, 15, 0, tzinfo=UTC)
    today = analytics.summary(period_key="today", now=now)

    assert today.feedback_topic_counts == {"nutrition": 2, "mental": 1}
    assert today.feedback_messages == 1


def test_analytics_summary_counts_donation_shown_and_clicks() -> None:
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001 - acceptable in focused unit test
        [
            AnalyticsEvent(
                name="donation_shown",
                user_id="u1",
                payload={"source": "donate_menu"},
                ts="2026-03-25T10:00:00+00:00",
            ),
            AnalyticsEvent(
                name="donation_clicked",
                user_id="u1",
                payload={"source": "donate_menu"},
                ts="2026-03-25T10:01:00+00:00",
            ),
            AnalyticsEvent(
                name="donation_shown",
                user_id="u2",
                payload={"source": "finish_improved"},
                ts="2026-03-25T11:00:00+00:00",
            ),
        ]
    )

    now = datetime(2026, 3, 25, 15, 0, tzinfo=UTC)
    today = analytics.summary(period_key="today", now=now)

    assert today.donation_shown_count == 2
    assert today.donation_clicks == 1


def test_analytics_restores_events_after_restart(tmp_path: Path) -> None:
    storage_path = tmp_path / "runtime" / "analytics_events.jsonl"

    analytics = Analytics(storage_path=storage_path)
    analytics.track("start", "u1", {"entry": "menu"})
    analytics.track("donation_clicked", "u1", {"source": "donate_menu"})
    analytics.close()

    restored = Analytics(storage_path=storage_path)
    summary = restored.summary(period_key="today")
    recent = restored.recent(limit=2)

    assert summary.event_counts["start"] == 1
    assert summary.donation_clicks == 1
    assert [event.name for event in recent] == ["start", "donation_clicked"]
    restored.close()


def test_analytics_summary_counts_app_types() -> None:
    analytics = Analytics()
    analytics.track("start", "u1", app_type="telegram")
    analytics.track("start", "u2", app_type="web")
    analytics.track("donation_clicked", "u3", {"source": "cta"}, app_type="mobile")

    summary = analytics.summary(period_key="today")

    assert summary.app_type_counts["telegram"] == 1
    assert summary.app_type_counts["web"] == 1
    assert summary.app_type_counts["mobile"] == 1


def test_analytics_rotates_storage_and_restores_recent_events(tmp_path: Path) -> None:
    storage_path = tmp_path / "runtime" / "analytics_events.jsonl"
    analytics = Analytics(
        storage_path=storage_path,
        storage_max_file_bytes=200,
        storage_backup_count=2,
        max_buffer=10,
    )

    analytics.track("start", "u1", {"blob": "x" * 180})
    analytics.track("start", "u2", {"blob": "y" * 180})
    analytics.track("start", "u3", {"blob": "z" * 180})
    analytics.close()

    assert storage_path.exists()
    assert storage_path.with_name(f"{storage_path.name}.1").exists()

    restored = Analytics(
        storage_path=storage_path,
        storage_max_file_bytes=200,
        storage_backup_count=2,
        max_buffer=10,
    )
    recent = restored.recent(limit=3)

    assert [event.user_id for event in recent] == ["u1", "u2", "u3"]
    restored.close()


def test_analytics_summary_merges_disk_events_from_other_runtime(tmp_path: Path) -> None:
    storage_path = tmp_path / "runtime" / "analytics_events.jsonl"
    bot_analytics = Analytics(storage_path=storage_path, max_buffer=10)
    api_analytics = Analytics(storage_path=storage_path, max_buffer=10)

    bot_analytics.track("start", "telegram-1", app_type="telegram")
    api_analytics.track("donation_clicked", "web-1", {"source": "redirect"}, app_type="web")
    api_analytics.close()

    summary = bot_analytics.summary(period_key="today")
    recent = bot_analytics.recent(limit=5)

    assert summary.event_counts["start"] == 1
    assert summary.donation_clicks == 1
    assert summary.app_type_counts["telegram"] == 1
    assert summary.app_type_counts["web"] == 1
    assert [event.name for event in recent] == ["start", "donation_clicked"]
    bot_analytics.close()


def test_analytics_restore_skips_malformed_lines(tmp_path: Path) -> None:
    storage_path = tmp_path / "runtime" / "analytics_events.jsonl"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        "\n".join(
            [
                '{"name":"start","user_id":"u1","payload":{"app_type":"telegram"},"ts":"2026-03-25T10:00:00+00:00"}',
                '{"name":"broken"',
                '{"name":"donation_clicked","user_id":"u2","payload":{"source":"cta","app_type":"web"},"ts":"2026-03-25T10:01:00+00:00"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analytics = Analytics(storage_path=storage_path, max_buffer=10)
    summary = analytics.summary(period_key="today", now=datetime(2026, 3, 25, 15, 0, tzinfo=UTC))

    assert summary.total_events == 2
    assert summary.event_counts["start"] == 1
    assert summary.donation_clicks == 1
    analytics.close()


def test_analytics_excludes_internal_users_from_summary_and_recent() -> None:
    analytics = Analytics(exclude_user_predicate=lambda user_id, app_type: user_id in {"1", "telegram:1"})
    analytics._buffer.extend(  # noqa: SLF001 - controlled timestamps for period filter
        [
            AnalyticsEvent(
                name="start",
                user_id="1",
                payload={"app_type": "telegram"},
                ts="2026-03-25T10:02:00+00:00",
            ),
            AnalyticsEvent(
                name="start",
                user_id="2",
                payload={"app_type": "telegram"},
                ts="2026-03-25T10:01:00+00:00",
            ),
            AnalyticsEvent(
                name="feedback_topic_selected",
                user_id="telegram:1",
                payload={"topic": "nutrition", "app_type": "telegram"},
                ts="2026-03-25T10:00:00+00:00",
            ),
        ]
    )
    summary = analytics.summary(period_key="today", now=datetime(2026, 3, 25, 15, 0, tzinfo=UTC))
    recent = analytics.recent(limit=10)

    assert summary.total_events == 1
    assert summary.event_counts["start"] == 1
    assert summary.feedback_topic_counts == {}
    assert [event.user_id for event in recent] == ["2"]


def test_analytics_summary_audience_splits_product_and_internal() -> None:
    ts = "2026-03-25T12:00:00+00:00"
    analytics = Analytics(exclude_user_predicate=lambda uid, app_type: uid == "1")
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent(
                name="start",
                user_id="user-a",
                payload={"app_type": "telegram"},
                ts=ts,
            ),
            AnalyticsEvent(
                name="start",
                user_id="1",
                payload={"app_type": "telegram"},
                ts=ts,
            ),
        ]
    )

    product = analytics.summary(period_key="today", audience="product", now=datetime(2026, 3, 25, 15, 0, tzinfo=UTC))
    internal = analytics.summary(period_key="today", audience="internal", now=datetime(2026, 3, 25, 15, 0, tzinfo=UTC))
    all_audiences = analytics.summary(period_key="today", audience="all", now=datetime(2026, 3, 25, 15, 0, tzinfo=UTC))

    assert product.total_events == 1
    assert internal.total_events == 1
    assert all_audiences.total_events == 2
    assert product.event_counts.get("start") == 1
    assert internal.event_counts.get("start") == 1


def test_product_and_internal_summaries_matches_separate_summary_calls() -> None:
    ts = "2026-03-25T12:00:00+00:00"
    analytics = Analytics(exclude_user_predicate=lambda uid, app_type: uid == "1")
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent(
                name="start",
                user_id="user-a",
                payload={"app_type": "telegram"},
                ts=ts,
            ),
            AnalyticsEvent(
                name="start",
                user_id="1",
                payload={"app_type": "telegram"},
                ts=ts,
            ),
        ]
    )
    now = datetime(2026, 3, 25, 15, 0, tzinfo=UTC)
    dual_p, dual_i = analytics.product_and_internal_summaries(period_key="today", now=now)
    sep_p = analytics.summary(period_key="today", audience="product", now=now)
    sep_i = analytics.summary(period_key="today", audience="internal", now=now)
    assert dual_p.total_events == sep_p.total_events == 1
    assert dual_i.total_events == sep_i.total_events == 1
    assert dual_p.event_counts == sep_p.event_counts
    assert dual_i.event_counts == sep_i.event_counts


def test_retention_returning_vs_new_today_utc() -> None:
    analytics = Analytics(exclude_user_predicate=lambda uid, _: uid == "admin")
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent("start", "u-ret", {}, "2026-03-24T10:00:00+00:00"),
            AnalyticsEvent("start", "u-new", {}, "2026-03-25T11:00:00+00:00"),
            AnalyticsEvent("start", "u-ret", {}, "2026-03-25T09:00:00+00:00"),
            AnalyticsEvent("start", "u-ret", {}, "2026-03-25T12:00:00+00:00"),
        ]
    )
    now = datetime(2026, 3, 25, 15, 0, tzinfo=ZoneInfo("UTC"))
    s = analytics.summary(period_key="today", now=now, audience="product")
    assert s.active_users == 2
    assert s.returning_users == 1
    assert s.new_users_in_period == 1
    assert s.returning_users + s.new_users_in_period == s.active_users
    assert s.multi_day_active_users == 0
    assert s.repeat_start_users == 1


def test_retention_multi_day_within_seven_days_utc() -> None:
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent("start", "u1", {}, "2026-03-20T10:00:00+00:00"),
            AnalyticsEvent(
                "state_selected",
                "u1",
                {"state": "anxious"},
                "2026-03-22T10:00:00+00:00",
            ),
        ]
    )
    now = datetime(2026, 3, 25, 15, 0, tzinfo=ZoneInfo("UTC"))
    s = analytics.summary(period_key="7d", now=now, audience="product")
    assert s.active_users == 1
    assert s.multi_day_active_users == 1


def test_analytics_summary_excludes_trace_events_from_funnel_totals() -> None:
    ts = "2026-03-25T12:00:00+00:00"
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent("start", "u1", {"app_type": "telegram"}, ts),
            AnalyticsEvent(
                EVENT_BOT_INTERACTION,
                "u1",
                {"app_type": "telegram", "kind": "callback", "prefix": "proto", "locale": "ru"},
                ts,
            ),
            AnalyticsEvent(
                EVENT_BOT_INTERACTION,
                "u1",
                {"app_type": "telegram", "kind": "callback", "prefix": "nav", "locale": "en"},
                ts,
            ),
        ]
    )
    now = datetime(2026, 3, 25, 15, 0, tzinfo=UTC)
    s = analytics.summary(period_key="today", now=now, audience="all", recent_limit=5)
    assert s.total_events == 1
    assert s.event_counts.get("start") == 1
    assert EVENT_BOT_INTERACTION not in s.event_counts
    assert len(s.recent_events) == 1
    assert s.recent_events[-1].name == "start"


def test_retention_repeat_start_same_calendar_day_not_multi_day() -> None:
    analytics = Analytics()
    analytics._buffer.extend(  # noqa: SLF001
        [
            AnalyticsEvent("start", "u1", {}, "2026-03-25T08:00:00+00:00"),
            AnalyticsEvent("start", "u1", {}, "2026-03-25T18:00:00+00:00"),
        ]
    )
    now = datetime(2026, 3, 25, 20, 0, tzinfo=ZoneInfo("UTC"))
    s = analytics.summary(period_key="today", now=now, audience="product")
    assert s.repeat_start_users == 1
    assert s.multi_day_active_users == 0
