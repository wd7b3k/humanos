from __future__ import annotations

import json
from pathlib import Path

from domain.protocol_engine import build_protocol_engine_from_release
from infrastructure.release_manifest import CURRENT_RELEASE_ID, CURRENT_RELEASE_VERSION
from infrastructure.release_store import ReleaseStore


def test_release_store_bootstraps_current_release(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path)

    releases = store.list_releases()
    events = store.recent_events(limit=5)

    assert releases
    assert releases[0].release_id == CURRENT_RELEASE_ID
    assert releases[0].active is True
    assert events
    assert events[0].release_id == CURRENT_RELEASE_ID


def test_release_store_can_activate_archived_release(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path)
    archive_release_id = "2026.01.15.1"
    archive_path = tmp_path / "data" / "protocol_releases" / "releases" / f"{archive_release_id}.json"
    current_data = store.get_active_release_data()
    archive_data = dict(current_data)
    archive_data["release_id"] = archive_release_id
    archive_data["version"] = archive_release_id
    archive_data["title"] = "Archived release"
    archive_data["notes"] = ["Older archived release"]
    archive_path.write_text(json.dumps(archive_data, ensure_ascii=False, indent=2), encoding="utf-8")
    registry_path = tmp_path / "data" / "protocol_releases" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["release_ids"].append(archive_release_id)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    record = store.activate_release(archive_release_id, actor="1", note="rollback test")

    assert record.release_id == archive_release_id
    assert store.list_releases()[0].release_id == archive_release_id
    assert store.list_releases()[0].active is True


def test_build_protocol_engine_from_release_uses_structured_fields(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path)
    engine = build_protocol_engine_from_release(store.get_active_release_data())

    step = engine.get_step("tired", 0, variant_id="main")
    release_meta = engine.current_release()

    assert step is not None
    assert step.how_to
    assert step.alternatives is not None
    assert step.release_id == CURRENT_RELEASE_ID
    assert release_meta["release_version"] == CURRENT_RELEASE_VERSION
