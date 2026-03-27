"""Lightweight file registry for protocol text releases and rollback."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from domain.protocol_engine import PROTOCOLS, _STATE_KEY_TO_RU, _split_step_body
from infrastructure.file_io import append_jsonl, atomic_write_json
from infrastructure.release_manifest import (
    CURRENT_RELEASE_ID,
    CURRENT_RELEASE_NOTES,
    CURRENT_RELEASE_TITLE,
    CURRENT_RELEASE_VERSION,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    release_id: str
    version: str
    title: str
    notes: tuple[str, ...]
    created_at: str
    active: bool


@dataclass(frozen=True, slots=True)
class ReleaseEvent:
    action: str
    release_id: str
    version: str
    actor: str
    ts: str
    note: str


class ReleaseStore:
    """Stores immutable release snapshots plus mutable active pointer."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root / "data" / "protocol_releases"
        self._releases_dir = self._root / "releases"
        self._registry_path = self._root / "registry.json"
        self._events_path = project_root / "data" / "runtime" / "release_events.jsonl"
        self._releases_dir.mkdir(parents=True, exist_ok=True)
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_bootstrapped()

    def _release_path(self, release_id: str) -> Path:
        return self._releases_dir / f"{release_id}.json"

    def _load_registry(self) -> dict[str, Any]:
        if not self._registry_path.is_file():
            return {"active_release_id": None, "release_ids": []}
        try:
            return dict(json.loads(self._registry_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid release registry: {self._registry_path}") from None
        except Exception:
            return {"active_release_id": None, "release_ids": []}

    def _save_registry(self, data: dict[str, Any]) -> None:
        atomic_write_json(self._registry_path, data, indent=2)

    def _append_event(self, action: str, *, release_id: str, version: str, actor: str, note: str) -> None:
        event = ReleaseEvent(
            action=action,
            release_id=release_id,
            version=version,
            actor=actor,
            ts=_now_iso(),
            note=note,
        )
        append_jsonl(self._events_path, asdict(event))

    def _build_bootstrap_release(self) -> dict[str, Any]:
        protocols: dict[str, Any] = {}
        for state_key, state_label in _STATE_KEY_TO_RU.items():
            spec = PROTOCOLS[state_label]
            steps: list[dict[str, Any]] = []
            for step in spec.steps:
                how_to, alternatives = _split_step_body(step.body)
                steps.append(
                    {
                        "phase": step.phase,
                        "title": step.title,
                        "duration_seconds": step.duration_seconds,
                        "how_to": how_to,
                        "alternatives": alternatives,
                        "goal": None,
                        "notes": None,
                    }
                )
            protocols[state_key] = {
                "state_label": state_label,
                "title": spec.title,
                "estimated_minutes": spec.estimated_minutes,
                "variants": [
                    {
                        "id": "main",
                        "label": "Основной",
                        "weight": 100,
                        "steps": steps,
                    }
                ],
            }
        return {
            "release_id": CURRENT_RELEASE_ID,
            "version": CURRENT_RELEASE_VERSION,
            "title": CURRENT_RELEASE_TITLE,
            "notes": list(CURRENT_RELEASE_NOTES),
            "created_at": _now_iso(),
            "protocols": protocols,
        }

    def ensure_bootstrapped(self) -> None:
        registry = self._load_registry()
        release_ids = [str(item) for item in registry.get("release_ids") or []]
        current_path = self._release_path(CURRENT_RELEASE_ID)
        created_current = False
        if not current_path.is_file():
            atomic_write_json(current_path, self._build_bootstrap_release(), indent=2)
            created_current = True
        if CURRENT_RELEASE_ID not in release_ids:
            release_ids.append(CURRENT_RELEASE_ID)
        active_release_id = str(registry.get("active_release_id") or "").strip() or CURRENT_RELEASE_ID
        if created_current or active_release_id not in release_ids:
            active_release_id = CURRENT_RELEASE_ID
        self._save_registry(
            {
                "active_release_id": active_release_id,
                "release_ids": release_ids,
            }
        )
        if created_current:
            self._append_event(
                "bootstrap",
                release_id=CURRENT_RELEASE_ID,
                version=CURRENT_RELEASE_VERSION,
                actor="system",
                note=CURRENT_RELEASE_TITLE,
            )

    def get_release_data(self, release_id: str) -> dict[str, Any]:
        path = self._release_path(release_id)
        return dict(json.loads(path.read_text(encoding="utf-8")))

    def get_active_release_data(self) -> dict[str, Any]:
        registry = self._load_registry()
        active_release_id = str(registry.get("active_release_id") or CURRENT_RELEASE_ID)
        return self.get_release_data(active_release_id)

    def list_releases(self) -> list[ReleaseRecord]:
        registry = self._load_registry()
        active_release_id = str(registry.get("active_release_id") or CURRENT_RELEASE_ID)
        records: list[ReleaseRecord] = []
        for release_id in reversed(list(registry.get("release_ids") or [])):
            data = self.get_release_data(str(release_id))
            records.append(
                ReleaseRecord(
                    release_id=str(data.get("release_id") or release_id),
                    version=str(data.get("version") or release_id),
                    title=str(data.get("title") or release_id),
                    notes=tuple(str(item) for item in data.get("notes") or ()),
                    created_at=str(data.get("created_at") or ""),
                    active=str(data.get("release_id") or release_id) == active_release_id,
                )
            )
        return records

    def activate_release(self, release_id: str, *, actor: str, note: str) -> ReleaseRecord:
        registry = self._load_registry()
        release_ids = [str(item) for item in registry.get("release_ids") or []]
        if release_id not in release_ids:
            raise KeyError(f"Unknown release {release_id}")
        data = self.get_release_data(release_id)
        self._save_registry(
            {
                "active_release_id": release_id,
                "release_ids": release_ids,
            }
        )
        self._append_event(
            "activate",
            release_id=release_id,
            version=str(data.get("version") or release_id),
            actor=actor,
            note=note,
        )
        return ReleaseRecord(
            release_id=str(data.get("release_id") or release_id),
            version=str(data.get("version") or release_id),
            title=str(data.get("title") or release_id),
            notes=tuple(str(item) for item in data.get("notes") or ()),
            created_at=str(data.get("created_at") or ""),
            active=True,
        )

    def recent_events(self, limit: int = 10) -> list[ReleaseEvent]:
        if not self._events_path.is_file():
            return []
        events: list[ReleaseEvent] = []
        with self._events_path.open(encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                data = json.loads(raw_line)
                events.append(
                    ReleaseEvent(
                        action=str(data.get("action") or ""),
                        release_id=str(data.get("release_id") or ""),
                        version=str(data.get("version") or ""),
                        actor=str(data.get("actor") or ""),
                        ts=str(data.get("ts") or ""),
                        note=str(data.get("note") or ""),
                    )
                )
        return list(reversed(events[-limit:]))
