"""Картинки для фаз протокола с устойчивым кэшем Telegram file_id."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from aiogram.types import FSInputFile, Message

from infrastructure.file_io import atomic_write_json

PHASE_ORDER: tuple[str, ...] = ("body", "breath", "attention", "adapt")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CACHE_PATH = _PROJECT_ROOT / "data" / "runtime" / "phase_file_ids_v2.json"
_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
_CACHE_LOCK = Lock()

PHASE_IMAGES: dict[str, Path] = {
    "body": _PROJECT_ROOT / "assets" / "humanos-phase-body.png",
    "breath": _PROJECT_ROOT / "assets" / "humanos-phase-breath.png",
    "attention": _PROJECT_ROOT / "assets" / "humanos-phase-attention.png",
    "adapt": _PROJECT_ROOT / "assets" / "humanos-phase-adapt.png",
}


def _load_phase_file_ids() -> dict[str, str]:
    if not _CACHE_PATH.is_file():
        return {}
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        str(phase): str(file_id)
        for phase, file_id in dict(data).items()
        if str(phase) in PHASE_ORDER and str(file_id).strip()
    }


_PHASE_FILE_IDS: dict[str, str] = _load_phase_file_ids()


def phase_by_step_index(step_index: int) -> str:
    if 0 <= step_index < len(PHASE_ORDER):
        return PHASE_ORDER[step_index]
    return "body"


def phase_media(step_index: int) -> tuple[str | FSInputFile | None, bool]:
    phase = phase_by_step_index(step_index)
    cached = _PHASE_FILE_IDS.get(phase)
    if cached:
        return cached, True
    path = PHASE_IMAGES.get(phase)
    if not path or not path.is_file():
        return None, False
    return FSInputFile(path), False


def remember_phase_file_id(step_index: int, sent_message: Message) -> None:
    """Cache Telegram file_id after the first successful upload."""
    phase = phase_by_step_index(step_index)
    if not sent_message.photo:
        return
    _PHASE_FILE_IDS[phase] = sent_message.photo[-1].file_id
    with _CACHE_LOCK:
        atomic_write_json(_CACHE_PATH, _PHASE_FILE_IDS)
