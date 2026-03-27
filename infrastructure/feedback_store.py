"""Persistent storage for text feedback messages from users."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from infrastructure.file_io import append_jsonl


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _coerce_ts(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _period_bounds(period_key: str, now: datetime) -> tuple[datetime, datetime]:
    local_now = now.astimezone()
    if period_key == "today":
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, local_now
    if period_key == "yesterday":
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return today_start - timedelta(days=1), today_start
    if period_key == "7d":
        return local_now - timedelta(days=7), local_now
    if period_key == "30d":
        return local_now - timedelta(days=30), local_now
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start, local_now


@dataclass(frozen=True, slots=True)
class FeedbackMessage:
    user_id: str
    username: str | None
    full_name: str | None
    text: str
    ts: str


class FeedbackStore:
    """Append-only JSONL storage for admin-readable text feedback."""

    def __init__(self, project_root: Path) -> None:
        runtime_dir = project_root / "data" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self._path = runtime_dir / "feedback_messages.jsonl"

    def _append_sync(
        self,
        *,
        user_id: int | str,
        text: str,
        username: str | None,
        full_name: str | None,
    ) -> FeedbackMessage:
        entry = FeedbackMessage(
            user_id=str(user_id),
            username=(username or "").strip() or None,
            full_name=(full_name or "").strip() or None,
            text=text,
            ts=_now_iso(),
        )
        append_jsonl(self._path, asdict(entry))
        return entry

    async def append(
        self,
        *,
        user_id: int | str,
        text: str,
        username: str | None = None,
        full_name: str | None = None,
    ) -> FeedbackMessage:
        return await asyncio.to_thread(
            self._append_sync,
            user_id=user_id,
            text=text,
            username=username,
            full_name=full_name,
        )

    def _recent_sync(
        self,
        *,
        period_key: str = "today",
        limit: int = 20,
        now: datetime | None = None,
    ) -> list[FeedbackMessage]:
        if not self._path.is_file():
            return []
        point_in_time = now or datetime.now(UTC)
        start, end = _period_bounds(period_key, point_in_time)
        items: list[FeedbackMessage] = []
        with self._path.open(encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                data = json.loads(raw_line)
                ts = _coerce_ts(str(data.get("ts") or _now_iso())).astimezone(start.tzinfo)
                if not (start <= ts < end):
                    continue
                items.append(
                    FeedbackMessage(
                        user_id=str(data.get("user_id") or ""),
                        username=data.get("username"),
                        full_name=data.get("full_name"),
                        text=str(data.get("text") or ""),
                        ts=ts.isoformat(),
                    )
                )
        return list(reversed(items[-limit:]))

    async def recent(
        self,
        *,
        period_key: str = "today",
        limit: int = 20,
        now: datetime | None = None,
    ) -> list[FeedbackMessage]:
        return await asyncio.to_thread(
            self._recent_sync,
            period_key=period_key,
            limit=limit,
            now=now,
        )
