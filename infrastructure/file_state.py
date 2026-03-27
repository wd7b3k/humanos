"""Файловое хранилище FSM и сессий пользователя (несколько процессов polling на одном сервере)."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aiogram.exceptions import DataNotDictLikeError
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from aiogram.fsm.state import State


class FileUserRepository:
    """Репозиторий сессий в JSON (общий для всех воркеров на одной машине)."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(user_id: int | str) -> str:
        return str(user_id)

    def _path(self, user_id: int | str) -> Path:
        return self._dir / f"{self._key(user_id)}.json"

    def _get_sync(self, user_id: int | str) -> dict[str, Any]:
        path = self._path(user_id)
        if not path.is_file():
            return {}
        with open(path, encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                raw = f.read()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if not raw.strip():
            return {}
        return dict(json.loads(raw))

    def _save_sync(self, user_id: int | str, data: dict[str, Any]) -> None:
        path = self._path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        with open(tmp, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(payload)
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        os.replace(tmp, path)

    async def get(self, user_id: int | str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_sync, user_id)

    async def save(self, user_id: int | str, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_sync, user_id, data)


class JsonFSMStorage(BaseStorage):
    """FSM aiogram в JSON-файлах (чтобы второй экземпляр бота видел те же состояния)."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: StorageKey) -> Path:
        tid = key.thread_id or 0
        bc = (key.business_connection_id or "").replace(os.sep, "_")
        name = f"{key.bot_id}_{key.chat_id}_{key.user_id}_{tid}_{bc}_{key.destiny}.json"
        return self._dir / name

    def _load(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {"state": None, "data": {}}
        with open(path, encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                raw = f.read()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if not raw.strip():
            return {"state": None, "data": {}}
        obj = json.loads(raw)
        return {"state": obj.get("state"), "data": dict(obj.get("data") or {})}

    def _update(self, path: Path, mutator) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Открываем для чтения+записи под эксклюзивной блокировкой (атомарно для файла).
        with open(path, "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                raw = f.read()
                if raw.strip():
                    rec = json.loads(raw)
                    record = {"state": rec.get("state"), "data": dict(rec.get("data") or {})}
                else:
                    record = {"state": None, "data": {}}
                mutator(record)
                f.seek(0)
                f.truncate()
                json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        path = self._path(key)
        st: str | None = state.state if isinstance(state, State) else state

        def _mut(rec: dict[str, Any]) -> None:
            rec["state"] = st

        await asyncio.to_thread(self._update, path, _mut)

    async def get_state(self, key: StorageKey) -> str | None:
        path = self._path(key)

        def _read() -> str | None:
            return self._load(path)["state"]

        return await asyncio.to_thread(_read)

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        if not isinstance(data, dict):
            msg = f"Data must be a dict or dict-like object, got {type(data).__name__}"
            raise DataNotDictLikeError(msg)
        path = self._path(key)

        def _mut(rec: dict[str, Any]) -> None:
            rec["data"] = dict(data)

        await asyncio.to_thread(self._update, path, _mut)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        path = self._path(key)

        def _read() -> dict[str, Any]:
            return dict(self._load(path)["data"])

        return await asyncio.to_thread(_read)

    async def close(self) -> None:
        pass
