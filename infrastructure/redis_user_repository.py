"""Сессии пользователей в Redis (масштабирование, много воркеров)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisUserRepository:
    """JSON одного пользователя в ключе Redis с опциональным TTL."""

    def __init__(self, redis: Redis, *, key_prefix: str, ttl_seconds: int | None = None) -> None:
        self._r = redis
        self._prefix = key_prefix.rstrip(":")
        self._ttl = ttl_seconds

    def _key(self, user_id: int | str) -> str:
        return f"{self._prefix}:session:{user_id}"

    async def get(self, user_id: int | str) -> dict[str, Any]:
        raw = await self._r.get(self._key(user_id))
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return dict(json.loads(raw))

    async def save(self, user_id: int | str, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False)
        k = self._key(user_id)
        if self._ttl:
            await self._r.set(k, payload, ex=self._ttl)
        else:
            await self._r.set(k, payload)
