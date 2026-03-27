from __future__ import annotations

import json
from pathlib import Path

from infrastructure.file_io import append_jsonl_batch


def test_append_jsonl_batch_writes_multiple_lines(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    append_jsonl_batch(path, [{"a": 1}, {"b": 2}], fsync=False)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"b": 2}
