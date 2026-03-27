"""Track runtime incidents and restart recovery state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from infrastructure.file_io import atomic_write_json


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class IncidentStatus:
    active: bool = False
    last_problem_at: str | None = None
    last_problem_reason: str | None = None
    last_resolved_at: str | None = None
    restart_count: int = 0


class IncidentStore:
    """Persist the latest bot incident under ``data/runtime``."""

    def __init__(self, project_root: Path) -> None:
        runtime_dir = project_root / "data" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self._path = runtime_dir / "incident_status.json"

    def snapshot(self) -> IncidentStatus:
        if not self._path.is_file():
            return IncidentStatus()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return IncidentStatus(
            active=bool(data.get("active")),
            last_problem_at=data.get("last_problem_at"),
            last_problem_reason=data.get("last_problem_reason"),
            last_resolved_at=data.get("last_resolved_at"),
            restart_count=int(data.get("restart_count") or 0),
        )

    def mark_problem(self, reason: str) -> IncidentStatus:
        prev = self.snapshot()
        status = IncidentStatus(
            active=True,
            last_problem_at=_now_iso(),
            last_problem_reason=reason.strip()[:500] or "unknown problem",
            last_resolved_at=prev.last_resolved_at,
            restart_count=prev.restart_count + 1,
        )
        self._save(status)
        return status

    def resolve_active(self) -> IncidentStatus | None:
        prev = self.snapshot()
        if not prev.active:
            return None
        status = IncidentStatus(
            active=False,
            last_problem_at=prev.last_problem_at,
            last_problem_reason=prev.last_problem_reason,
            last_resolved_at=_now_iso(),
            restart_count=prev.restart_count,
        )
        self._save(status)
        return prev

    def _save(self, status: IncidentStatus) -> None:
        atomic_write_json(self._path, asdict(status))
