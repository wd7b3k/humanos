"""Telegram middleware that stores stable and public identity hints."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from aiogram import BaseMiddleware

from app.use_cases.context import AppContext
from app.use_cases.identity import IdentityCaptureUseCase

log = logging.getLogger(__name__)

# Skip full identity sync when profile fields unchanged and synced recently (avoids DB on every tap).
_MAX_FINGERPRINT_CACHE = 50_000


class TelegramIdentityMiddleware(BaseMiddleware):
    def __init__(self, ctx: AppContext) -> None:
        self._capture = IdentityCaptureUseCase(ctx)
        self._resync_seconds = float(ctx.settings.bot_identity_resync_seconds)

    _fingerprints: ClassVar[dict[int, tuple[tuple[str | None, str | None, str | None], float]]] = {}
    _sync_locks: ClassVar[dict[int, asyncio.Lock]] = {}

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is not None:
            fp = (user.username, user.full_name, user.language_code)
            now = time.monotonic()
            uid = user.id
            ent = self._fingerprints.get(uid)
            skip = (
                ent is not None
                and ent[0] == fp
                and (now - ent[1]) < self._resync_seconds
            )
            if not skip:
                lock = self._sync_locks.setdefault(uid, asyncio.Lock())
                async with lock:
                    await self._capture.sync_telegram_identity(
                        user_id=user.id,
                        username=user.username,
                        full_name=user.full_name,
                        language_code=user.language_code,
                    )
                if len(self._fingerprints) >= _MAX_FINGERPRINT_CACHE:
                    drop = max(1, _MAX_FINGERPRINT_CACHE // 5)
                    for stale in list(self._fingerprints.keys())[:drop]:
                        self._fingerprints.pop(stale, None)
                    log.info("identity fingerprint cache trimmed by %s (cap %s)", drop, _MAX_FINGERPRINT_CACHE)
                self._fingerprints[uid] = (fp, now)
        return await handler(event, data)
