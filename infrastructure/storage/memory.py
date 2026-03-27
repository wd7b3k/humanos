"""In-process storage for development and tests."""

from __future__ import annotations

import asyncio
import copy
from typing import Any


class InMemoryUserRepository:
    """Async in-memory backend (один процесс)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(user_id: int | str) -> str:
        return str(user_id)

    async def get(self, user_id: int | str) -> dict[str, Any]:
        async with self._lock:
            raw = self._store.get(self._key(user_id))
            return copy.deepcopy(raw) if raw else {}

    async def save(self, user_id: int | str, data: dict[str, Any]) -> None:
        async with self._lock:
            self._store[self._key(user_id)] = copy.deepcopy(data)
