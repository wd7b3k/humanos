"""Обложки для разделов бота с кэшем Telegram file_id."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from aiogram.types import FSInputFile, Message

from infrastructure.file_io import atomic_write_json

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CACHE_PATH = _PROJECT_ROOT / "data" / "runtime" / "section_file_ids_v4.json"
_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
_CACHE_LOCK = Lock()

SECTION_IMAGES: dict[str, Path] = {
    "start_choice": _PROJECT_ROOT / "assets" / "humanos-start-choice-cover.jpg",
    "about_intro": _PROJECT_ROOT / "assets" / "humanos-about-cover.jpg",
    "about_how": _PROJECT_ROOT / "assets" / "humanos-how-it-works-cover.jpg",
    "donate": _PROJECT_ROOT / "assets" / "humanos-donate-cover.jpg",
    "feedback": _PROJECT_ROOT / "assets" / "humanos-feedback-cover.jpg",
    "practice_end": _PROJECT_ROOT / "assets" / "humanos-finish-cover.jpg",
}


def _load_file_ids() -> dict[str, str]:
    if not _CACHE_PATH.is_file():
        return {}
    try:
        raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        str(key): str(value)
        for key, value in dict(raw).items()
        if str(key) in SECTION_IMAGES and str(value).strip()
    }


_SECTION_FILE_IDS: dict[str, str] = _load_file_ids()


def section_media(section_key: str) -> tuple[str | FSInputFile | None, bool]:
    cached = _SECTION_FILE_IDS.get(section_key)
    if cached:
        return cached, True
    path = SECTION_IMAGES.get(section_key)
    if not path or not path.is_file():
        return None, False
    return FSInputFile(path), False


def remember_section_file_id(section_key: str, sent_message: Message) -> None:
    """Сохраняет Telegram file_id после первой успешной отправки."""
    if section_key not in SECTION_IMAGES or not sent_message.photo:
        return
    _SECTION_FILE_IDS[section_key] = sent_message.photo[-1].file_id
    with _CACHE_LOCK:
        atomic_write_json(_CACHE_PATH, _SECTION_FILE_IDS)
