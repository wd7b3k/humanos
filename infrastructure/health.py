"""Runtime health snapshot helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.use_cases.context import AppContext


@dataclass(frozen=True, slots=True)
class RuntimeHealthSnapshot:
    status: str
    checked_at: str
    component: str
    env: str
    transport_mode: str
    storage_backend: str
    api_auth_enabled: bool
    active_incident: bool
    restart_count: int
    last_problem_at: str | None
    last_problem_reason: str | None
    last_resolved_at: str | None
    release_id: str | None
    release_version: str | None
    client_db: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_runtime_health(ctx: AppContext, *, component: str) -> RuntimeHealthSnapshot:
    incident = ctx.incidents.snapshot()
    release_meta = ctx.protocols.current_release()
    return RuntimeHealthSnapshot(
        status="degraded" if incident.active else "ok",
        checked_at=datetime.now(UTC).isoformat(),
        component=component,
        env=ctx.settings.env,
        transport_mode=ctx.settings.transport_mode if component == "bot" else "api",
        storage_backend="redis" if ctx.settings.use_redis else "file",
        api_auth_enabled=ctx.settings.api_auth_enabled,
        active_incident=incident.active,
        restart_count=incident.restart_count,
        last_problem_at=incident.last_problem_at,
        last_problem_reason=incident.last_problem_reason,
        last_resolved_at=incident.last_resolved_at,
        release_id=str(release_meta.get("release_id") or "") or None,
        release_version=str(release_meta.get("release_version") or "") or None,
        client_db=ctx.clients.health_snapshot_sync(),
    )
