"""Small helpers for safer local file persistence."""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
    tmp_path.write_text(text, encoding=encoding)
    os.replace(tmp_path, path)


def atomic_write_json(path: Path, payload: Any, *, encoding: str = "utf-8", indent: int | None = None) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")),
        encoding=encoding,
    )


def append_jsonl(path: Path, payload: Any, *, encoding: str = "utf-8", fsync: bool = False) -> None:
    append_jsonl_batch(path, (payload,), encoding=encoding, fsync=fsync)


def append_jsonl_batch(
    path: Path,
    payloads: Iterable[Any],
    *,
    encoding: str = "utf-8",
    fsync: bool = False,
) -> None:
    """Append several JSON lines under one file lock (без fsync по умолчанию — для нагрузки)."""
    lines: list[str] = []
    for payload in payloads:
        lines.append(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(lines)
    with path.open("a", encoding=encoding) as f:
        fd = f.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            f.write(data)
            f.flush()
            if fsync:
                os.fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
