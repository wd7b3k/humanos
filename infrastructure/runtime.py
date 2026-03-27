"""Сборка хранилищ: Redis (нагрузка) или файлы (dev)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage
from aiogram.fsm.storage.memory import SimpleEventIsolation

from app.use_cases.context import AppContext
from domain.protocol_engine import build_protocol_engine_from_release
from infrastructure.analytics import Analytics
from infrastructure.auth_tokens import AuthTokenCodec
from infrastructure.client_store import ClientStore
from infrastructure.config import Settings
from infrastructure.file_state import FileUserRepository, JsonFSMStorage
from infrastructure.feedback_store import FeedbackStore
from infrastructure.incidents import IncidentStore
from infrastructure.push import default_push_triggers
from infrastructure.release_store import ReleaseStore
from infrastructure.redis_user_repository import RedisUserRepository
from infrastructure.storage.repository import UserRepository

ShutdownHook = Callable[[], Awaitable[None]]

log = logging.getLogger(__name__)


@dataclass(slots=True)
class BotRuntime:
    """Контекст приложения + FSM + хуки закрытия (Redis pool)."""

    ctx: AppContext
    fsm_storage: BaseStorage
    event_isolation: BaseEventIsolation
    shutdown_hooks: list[ShutdownHook]


@dataclass(slots=True)
class SharedContextDeps:
    analytics: Analytics
    release_store: ReleaseStore
    protocols: object
    incidents: IncidentStore
    feedback_store: FeedbackStore
    clients: ClientStore
    auth_tokens: AuthTokenCodec
    push_triggers: tuple


async def _noop_shutdown() -> None:
    return None


async def _close_analytics(analytics: Analytics) -> None:
    await asyncio.to_thread(analytics.close)


def _build_internal_actor_predicate(settings: Settings, clients: ClientStore) -> Callable[[str, str], bool]:
    cache: dict[tuple[str, str], tuple[bool, float]] = {}
    cache_ttl_seconds = 60.0

    def _candidates(user_id: str, app_type: str) -> list[tuple[str, str]]:
        uid = (user_id or "").strip()
        normalized_app_type = (app_type or "").strip().lower()
        candidates: list[tuple[str, str]] = []
        if ":" in uid:
            provider, subject = uid.split(":", 1)
            if provider and subject:
                candidates.append((provider.lower(), subject))
        elif uid.startswith("telegram-"):
            candidates.append(("telegram", uid.split("-", 1)[1]))
        elif uid.isdigit():
            candidates.append(("telegram", uid))
            if normalized_app_type:
                candidates.append((normalized_app_type, uid))
        elif normalized_app_type:
            candidates.append((normalized_app_type, uid))
        return candidates

    def _predicate(user_id: str, app_type: str) -> bool:
        uid = (user_id or "").strip()
        if uid.isdigit() and settings.is_admin(uid):
            return True
        for provider, subject in _candidates(uid, app_type):
            if provider == "telegram" and subject.isdigit() and settings.is_admin(subject):
                return True
            cache_key = (provider, subject)
            cached = cache.get(cache_key)
            now = monotonic()
            if cached is not None and cached[1] > now:
                if cached[0]:
                    return True
                continue
            is_internal = clients.is_internal_identity_sync(provider, subject)
            cache[cache_key] = (is_internal, now + cache_ttl_seconds)
            if is_internal:
                return True
        return False

    return _predicate


def _build_shared_context_deps(settings: Settings, *, default_app_type: str) -> SharedContextDeps:
    runtime_dir = settings.project_root / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    client_store = ClientStore(settings.client_db_path, admin_ids=settings.admin_ids)
    if settings.is_prod and not settings.use_redis:
        log.warning(
            "HumanOS prod без REDIS_URL: при рекламном трафике задайте Redis для FSM и сессий, "
            "файловый бэкенд не рассчитан на десятки тысяч одновременных диалогов."
        )
    analytics = Analytics(
        storage_path=runtime_dir / "analytics_events.jsonl",
        default_app_type=default_app_type,
        storage_max_file_bytes=settings.analytics_max_file_bytes,
        storage_backup_count=settings.analytics_backup_count,
        exclude_user_predicate=_build_internal_actor_predicate(settings, client_store),
        writer_batch_size=settings.analytics_writer_batch_size,
        writer_flush_interval=settings.analytics_writer_flush_seconds,
        writer_queue_maxsize=settings.analytics_writer_queue_max,
    )
    release_store = ReleaseStore(settings.project_root)
    return SharedContextDeps(
        analytics=analytics,
        release_store=release_store,
        protocols=build_protocol_engine_from_release(release_store.get_active_release_data()),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        clients=client_store,
        auth_tokens=AuthTokenCodec(
            settings.auth_token_secret,
            ttl_seconds=settings.auth_token_ttl_seconds,
        ),
        push_triggers=default_push_triggers(),
    )


async def build_bot_runtime(settings: Settings) -> BotRuntime:
    """
    Redis (рекомендуется для тысяч одновременных диалогов): один клиент на FSM и сессии.

    Пакет ``redis`` нужен только если задан ``REDIS_URL``. Без него — JSON на диске.
    """
    from aiogram.fsm.storage.base import DefaultKeyBuilder
    from aiogram.fsm.storage.redis import RedisStorage

    runtime_dir = settings.project_root / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shared = _build_shared_context_deps(settings, default_app_type="telegram")
    hooks: list[ShutdownHook] = []
    hooks.append(lambda: _close_analytics(shared.analytics))

    if settings.use_redis:
        assert settings.redis_url is not None
        fsm_storage = RedisStorage.from_url(
            settings.redis_url,
            key_builder=DefaultKeyBuilder(prefix=f"{settings.redis_key_prefix}:fsm"),
            state_ttl=settings.fsm_ttl_seconds,
            data_ttl=settings.fsm_ttl_seconds,
        )
        users: UserRepository = RedisUserRepository(
            fsm_storage.redis,
            key_prefix=settings.redis_key_prefix,
            ttl_seconds=settings.session_ttl_seconds,
        )
        isolation: BaseEventIsolation = fsm_storage.create_isolation()

        async def _close_redis() -> None:
            await fsm_storage.close()

        hooks.append(_close_redis)
    else:
        fsm_storage = JsonFSMStorage(runtime_dir / "fsm")
        users = FileUserRepository(runtime_dir / "sessions")
        isolation = SimpleEventIsolation()
        hooks.append(_noop_shutdown)

    ctx = AppContext(
        settings=settings,
        users=users,
        analytics=shared.analytics,
        protocols=shared.protocols,
        incidents=shared.incidents,
        feedback_store=shared.feedback_store,
        release_store=shared.release_store,
        clients=shared.clients,
        auth_tokens=shared.auth_tokens,
        push_triggers=shared.push_triggers,
    )

    return BotRuntime(
        ctx=ctx,
        fsm_storage=fsm_storage,
        event_isolation=isolation,
        shutdown_hooks=hooks,
    )


async def build_api_context(settings: Settings) -> tuple[AppContext, list[ShutdownHook]]:
    """HTTP API: сессии Redis/файлы; отдельный пул Redis от бота (если включён)."""
    runtime_dir = settings.project_root / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shared = _build_shared_context_deps(settings, default_app_type="api")
    hooks: list[ShutdownHook] = []
    hooks.append(lambda: _close_analytics(shared.analytics))

    if settings.use_redis:
        from redis.asyncio import Redis

        assert settings.redis_url is not None
        redis = Redis.from_url(settings.redis_url, decode_responses=False)
        users: UserRepository = RedisUserRepository(
            redis,
            key_prefix=settings.redis_key_prefix,
            ttl_seconds=settings.session_ttl_seconds,
        )

        async def _close() -> None:
            await redis.aclose(close_connection_pool=True)

        hooks.append(_close)
    else:
        users = FileUserRepository(runtime_dir / "sessions")
        hooks.append(_noop_shutdown)

    ctx = AppContext(
        settings=settings,
        users=users,
        analytics=shared.analytics,
        protocols=shared.protocols,
        incidents=shared.incidents,
        feedback_store=shared.feedback_store,
        release_store=shared.release_store,
        clients=shared.clients,
        auth_tokens=shared.auth_tokens,
        push_triggers=shared.push_triggers,
    )
    return ctx, hooks
