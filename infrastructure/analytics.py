"""Event tracking: in-memory ring buffer + optional disk persistence."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections import deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from queue import Empty, Full, Queue
from threading import RLock, Thread
from typing import Any, Callable, Literal

from infrastructure.file_io import append_jsonl_batch
from shared.constants import ANALYTICS_TRACE_EVENT_NAMES
from shared.locale import analytics_period_label, normalize_locale


log = logging.getLogger(__name__)

AnalyticsAudience = Literal["product", "internal", "all"]

ANALYTICS_PERIODS: dict[str, str] = {
    "today": "Сегодня",
    "yesterday": "Вчера",
    "7d": "7 дней",
    "30d": "30 дней",
}


def _coerce_ts(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _period_bounds(period_key: str, now: datetime) -> tuple[datetime, datetime]:
    local_now = now.astimezone()
    if period_key == "today":
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = local_now
        return start, end
    if period_key == "yesterday":
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today_start - timedelta(days=1)
        end = today_start
        return start, end
    if period_key == "7d":
        return local_now - timedelta(days=7), local_now
    if period_key == "30d":
        return local_now - timedelta(days=30), local_now
    raise ValueError(f"Unknown analytics period: {period_key}")


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    """Single recorded event."""

    name: str
    user_id: str
    payload: dict[str, Any]
    ts: str


def _is_trace_event(ev: AnalyticsEvent) -> bool:
    return ev.name in ANALYTICS_TRACE_EVENT_NAMES


def _local_date(ev: AnalyticsEvent, tz: tzinfo | None) -> date:
    return _coerce_ts(ev.ts).astimezone(tz).date()


def _compute_retention(
    *,
    period_events: list[AnalyticsEvent],
    history_events: list[AnalyticsEvent],
    period_start: datetime,
) -> tuple[int, int, int, int, int]:
    """
    Retention helpers from event tails (history_events must include period_events timespan).

    - active_users: distinct user_id with ≥1 event in the period
    - returning_users: active in period and had ≥1 event strictly before period_start (in snapshot)
    - new_users_in_period: active but not returning (first snapshot touch in window is in-period)
    - multi_day_active_users: active users with events on ≥2 local calendar days inside the period
    - repeat_start_users: users with ≥2 ``start`` events in the period

    Snapshots are tail-limited; "new" can be overstated if earlier history was rotated away.
    """
    tz = period_start.tzinfo
    period_users = {ev.user_id for ev in period_events if ev.user_id}
    prior_users = {
        ev.user_id
        for ev in history_events
        if ev.user_id and _coerce_ts(ev.ts).astimezone(period_start.tzinfo) < period_start
    }
    active = len(period_users)
    returning = len(period_users & prior_users)
    new_in_period = len(period_users - prior_users)

    user_days: dict[str, set[date]] = {}
    for ev in period_events:
        if not ev.user_id:
            continue
        user_days.setdefault(ev.user_id, set()).add(_local_date(ev, tz))
    multi_day = sum(1 for days in user_days.values() if len(days) >= 2)

    start_counts: Counter[str] = Counter()
    for ev in period_events:
        if ev.name == "start" and ev.user_id:
            start_counts[ev.user_id] += 1
    repeat_starts = sum(1 for c in start_counts.values() if c >= 2)

    return active, returning, new_in_period, multi_day, repeat_starts


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    """Admin-friendly aggregate snapshot."""

    generated_at: str
    period_key: str
    period_label: str
    total_events: int
    event_counts: dict[str, int]
    app_type_counts: dict[str, int]
    state_counts: dict[str, int]
    feedback_topic_counts: dict[str, int]
    started_protocols: int
    completed_protocols: int
    improved_count: int
    donation_shown_count: int
    donation_clicks: int
    feedback_messages: int
    active_users: int
    returning_users: int
    new_users_in_period: int
    multi_day_active_users: int
    repeat_start_users: int
    recent_events: list[AnalyticsEvent]


_SNAPSHOT_LINE_CAP = 50_000
_RETENTION_SNAPSHOT_FLOOR = 8_000


class Analytics:
    """
    ``track(event_name, user_id, payload= {})`` — no external IO except logs.

    Internal/admin actors are still persisted; use ``summary(..., audience="product")`` to exclude them from aggregates.

    Swap implementation later for Segment, ClickHouse, etc., keeping the same API.
    """

    def __init__(
        self,
        *,
        max_buffer: int = 10_000,
        emit_logs: bool = False,
        storage_path: Path | None = None,
        default_app_type: str = "unknown",
        storage_max_file_bytes: int = 5 * 1024 * 1024,
        storage_backup_count: int = 3,
        exclude_user_predicate: Callable[[str, str], bool] | None = None,
        writer_batch_size: int = 200,
        writer_flush_interval: float = 0.25,
        writer_queue_maxsize: int = 200_000,
    ) -> None:
        self._max_buffer = max_buffer
        self._buffer: deque[AnalyticsEvent] = deque(maxlen=max_buffer)
        self._lock = RLock()
        self._emit_logs = emit_logs
        self._storage_path = storage_path
        self._default_app_type = (default_app_type or "unknown").strip().lower()
        self._storage_max_file_bytes = max(0, int(storage_max_file_bytes))
        self._storage_backup_count = max(0, int(storage_backup_count))
        self._exclude_user_predicate = exclude_user_predicate
        self._writer_batch_size = max(1, int(writer_batch_size))
        self._writer_flush_interval = max(0.05, float(writer_flush_interval))
        self._writer_queue_maxsize = max(1000, int(writer_queue_maxsize))
        self._persist_dropped = 0
        self._last_drop_log_at = 0.0
        self._writer_queue: Queue[AnalyticsEvent | None] | None = None
        self._writer_thread: Thread | None = None
        if self._storage_path is not None:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()
            self._start_writer()

    def _start_writer(self) -> None:
        if self._storage_path is None or self._writer_thread is not None:
            return
        self._writer_queue = Queue(maxsize=self._writer_queue_maxsize)
        self._writer_thread = Thread(target=self._writer_loop, name="analytics-writer", daemon=True)
        self._writer_thread.start()

    def _load_from_disk(self) -> None:
        if self._storage_path is None:
            return
        try:
            for event in self._read_disk_events(max_events=self._max_buffer):
                self._buffer.append(event)
        except Exception:
            log.exception("analytics restore failed from %s", self._storage_path)

    @staticmethod
    def _event_from_json(data: dict[str, Any]) -> AnalyticsEvent:
        return AnalyticsEvent(
            name=str(data.get("name") or ""),
            user_id=str(data.get("user_id") or ""),
            payload=dict(data.get("payload") or {}),
            ts=str(data.get("ts") or datetime.now(UTC).isoformat()),
        )

    @staticmethod
    def _event_key(event: AnalyticsEvent) -> tuple[str, str, str, str]:
        return (
            event.name,
            event.user_id,
            event.ts,
            json.dumps(event.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )

    def _read_disk_events(self, *, max_events: int) -> list[AnalyticsEvent]:
        if self._storage_path is None or max_events <= 0:
            return []
        recent_lines: deque[str] = deque(maxlen=max_events)
        for path in self._restore_paths():
            if not path.is_file():
                continue
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        recent_lines.append(line)
        events: list[AnalyticsEvent] = []
        for raw_line in recent_lines:
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                log.warning("analytics skipped malformed line from %s", self._storage_path)
                continue
            events.append(self._event_from_json(data))
        return events

    def _snapshot_events(self, *, min_events: int = 0) -> list[AnalyticsEvent]:
        target_size = max(self._max_buffer * 2, min_events)
        with self._lock:
            memory_events = list(self._buffer)
        if self._storage_path is None:
            return memory_events[-target_size:]
        merged: list[AnalyticsEvent] = []
        seen: set[tuple[str, str, str, str]] = set()
        for event in [*self._read_disk_events(max_events=target_size), *memory_events]:
            key = self._event_key(event)
            if key in seen:
                continue
            seen.add(key)
            merged.append(event)
        merged.sort(key=lambda ev: _coerce_ts(ev.ts))
        return merged[-target_size:]

    def _restore_paths(self) -> list[Path]:
        if self._storage_path is None:
            return []
        paths: list[Path] = []
        for idx in range(self._storage_backup_count, 0, -1):
            paths.append(self._storage_path.with_name(f"{self._storage_path.name}.{idx}"))
        paths.append(self._storage_path)
        return paths

    def _maybe_rotate_storage(self) -> None:
        if (
            self._storage_path is None
            or self._storage_max_file_bytes <= 0
            or not self._storage_path.exists()
            or self._storage_path.stat().st_size < self._storage_max_file_bytes
        ):
            return
        if self._storage_backup_count <= 0:
            self._storage_path.unlink(missing_ok=True)
            return
        oldest = self._storage_path.with_name(f"{self._storage_path.name}.{self._storage_backup_count}")
        oldest.unlink(missing_ok=True)
        for idx in range(self._storage_backup_count - 1, 0, -1):
            src = self._storage_path.with_name(f"{self._storage_path.name}.{idx}")
            dst = self._storage_path.with_name(f"{self._storage_path.name}.{idx + 1}")
            if src.exists():
                src.replace(dst)
        self._storage_path.replace(self._storage_path.with_name(f"{self._storage_path.name}.1"))
        self._storage_path.touch()

    def _writer_loop(self) -> None:
        if self._storage_path is None or self._writer_queue is None:
            return
        batch: list[dict[str, Any]] = []
        pending_task_done = 0

        def flush_batch() -> None:
            nonlocal batch, pending_task_done
            if not batch or self._storage_path is None:
                return
            try:
                self._maybe_rotate_storage()
                append_jsonl_batch(self._storage_path, batch, fsync=False)
                self._maybe_rotate_storage()
            except Exception:
                log.exception("analytics persist failed to %s", self._storage_path)
            finally:
                for _ in range(pending_task_done):
                    self._writer_queue.task_done()
                batch.clear()
                pending_task_done = 0

        while True:
            timeout = self._writer_flush_interval if batch else 0.5
            try:
                item = self._writer_queue.get(timeout=timeout)
            except Empty:
                flush_batch()
                continue
            if item is None:
                flush_batch()
                self._writer_queue.task_done()
                break
            batch.append(
                {
                    "name": item.name,
                    "user_id": item.user_id,
                    "payload": item.payload,
                    "ts": item.ts,
                }
            )
            pending_task_done += 1
            if len(batch) >= self._writer_batch_size:
                flush_batch()

    def close(self, *, timeout_seconds: float = 10.0) -> None:
        if self._writer_queue is None or self._writer_thread is None:
            return
        self._writer_queue.put(None)
        self._writer_thread.join(timeout=timeout_seconds)
        if self._writer_thread.is_alive():
            log.warning("analytics writer did not stop within %.1fs", timeout_seconds)
        self._writer_queue = None
        self._writer_thread = None

    def track(
        self,
        event_name: str,
        user_id: int | str,
        payload: dict | None = None,
        *,
        app_type: str | None = None,
    ) -> None:
        """Record an analytics event (all users; filter in ``summary`` / ``recent`` via ``audience``)."""
        p = dict(payload or {})
        normalized_app_type = str(app_type or p.get("app_type") or self._default_app_type or "unknown").strip().lower()
        p["app_type"] = normalized_app_type
        uid = str(user_id)
        ev = AnalyticsEvent(
            name=event_name,
            user_id=uid,
            payload=p,
            ts=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._buffer.append(ev)
        if self._writer_queue is not None:
            try:
                self._writer_queue.put_nowait(ev)
            except Full:
                self._persist_dropped += 1
                now_m = time.monotonic()
                if now_m - self._last_drop_log_at >= 60.0:
                    log.warning(
                        "analytics writer queue full (max=%s), dropped %s disk writes since last log",
                        self._writer_queue_maxsize,
                        self._persist_dropped,
                    )
                    self._last_drop_log_at = now_m
        if self._emit_logs and log.isEnabledFor(logging.INFO):
            log.info("analytics | %s | user=%s | %s", event_name, uid, p)
        elif log.isEnabledFor(logging.DEBUG):
            log.debug("analytics | %s | user=%s | %s", event_name, uid, p)

    def recent(self, limit: int = 100, *, audience: AnalyticsAudience = "product") -> list[AnalyticsEvent]:
        """Debug / admin: last N events."""
        events = [ev for ev in self._snapshot_events(min_events=limit) if self._audience_match(ev, audience)]
        return events[-limit:]

    def _should_exclude(self, user_id: str, app_type: str) -> bool:
        if self._exclude_user_predicate is None:
            return False
        try:
            return bool(self._exclude_user_predicate(user_id, app_type))
        except Exception:
            log.exception("analytics exclusion predicate failed for user=%s app_type=%s", user_id, app_type)
            return False

    def _audience_match(self, event: AnalyticsEvent, audience: AnalyticsAudience) -> bool:
        if audience == "all":
            return True
        excluded = self._should_exclude(event.user_id, str(event.payload.get("app_type") or "unknown"))
        if audience == "product":
            return not excluded
        if audience == "internal":
            return excluded
        return True

    def _summary_snapshot_budget(self, recent_limit: int) -> int:
        """Lines to read for aggregates + retention (tail of log / buffer)."""
        return min(
            _SNAPSHOT_LINE_CAP,
            max(self._max_buffer * 2, recent_limit, _RETENTION_SNAPSHOT_FLOOR),
        )

    def summary(
        self,
        *,
        period_key: str = "today",
        recent_limit: int = 10,
        now: datetime | None = None,
        audience: AnalyticsAudience = "product",
        locale: str | None = None,
    ) -> AnalyticsSummary:
        """Return aggregate counters for the admin panel."""
        if period_key not in ANALYTICS_PERIODS:
            period_key = "today"
        loc = normalize_locale(locale)
        point_in_time = now or datetime.now(UTC)
        start, end = _period_bounds(period_key, point_in_time)
        snapshot = self._snapshot_events(min_events=self._summary_snapshot_budget(recent_limit))
        history_matched = [ev for ev in snapshot if self._audience_match(ev, audience)]
        events = [
            ev
            for ev in history_matched
            if start <= _coerce_ts(ev.ts).astimezone(start.tzinfo) < end
        ]
        funnel_events = [ev for ev in events if not _is_trace_event(ev)]

        active_users, returning_users, new_users_in_period, multi_day_active_users, repeat_start_users = (
            _compute_retention(
                period_events=events,
                history_events=history_matched,
                period_start=start,
            )
        )

        event_counts = Counter(ev.name for ev in funnel_events)
        app_type_counts = Counter(
            str(ev.payload.get("app_type") or "unknown")
            for ev in funnel_events
        )
        state_counts = Counter(
            str(ev.payload.get("state"))
            for ev in funnel_events
            if ev.name == "state_selected" and ev.payload.get("state")
        )
        feedback_topic_users: dict[str, set[str]] = {}
        for ev in funnel_events:
            if ev.name != "feedback_topic_selected":
                continue
            topic = str(ev.payload.get("topic") or "").strip()
            if not topic:
                continue
            feedback_topic_users.setdefault(topic, set()).add(ev.user_id)
        feedback_topic_counts = {
            topic: len(users)
            for topic, users in sorted(
                feedback_topic_users.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
        }
        recent_events = funnel_events[-recent_limit:]
        return AnalyticsSummary(
            generated_at=point_in_time.astimezone().isoformat(),
            period_key=period_key,
            period_label=analytics_period_label(loc, period_key),
            total_events=len(funnel_events),
            event_counts=dict(event_counts),
            app_type_counts=dict(app_type_counts),
            state_counts=dict(state_counts),
            feedback_topic_counts=feedback_topic_counts,
            started_protocols=event_counts.get("protocol_started", 0),
            completed_protocols=event_counts.get("protocol_completed", 0),
            improved_count=event_counts.get("improved", 0),
            donation_shown_count=event_counts.get("donation_shown", 0),
            donation_clicks=event_counts.get("donation_clicked", 0),
            feedback_messages=event_counts.get("feedback_message_sent", 0),
            active_users=active_users,
            returning_users=returning_users,
            new_users_in_period=new_users_in_period,
            multi_day_active_users=multi_day_active_users,
            repeat_start_users=repeat_start_users,
            recent_events=recent_events,
        )
