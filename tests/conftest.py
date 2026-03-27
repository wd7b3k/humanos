from __future__ import annotations

from pathlib import Path

import pytest

from app.use_cases.context import AppContext
from domain.protocols import build_default_protocol_engine
from infrastructure.analytics import Analytics
from infrastructure.auth_tokens import AuthTokenCodec
from infrastructure.client_store import ClientStore
from infrastructure.config import Settings
from infrastructure.feedback_store import FeedbackStore
from infrastructure.incidents import IncidentStore
from infrastructure.push import default_push_triggers
from infrastructure.release_store import ReleaseStore
from infrastructure.storage.memory import InMemoryUserRepository


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        bot_token="test-token",
        tribute_url="https://tribute.tg/test",
        bot_public_url="https://t.me/HumanOS_robot",
        env="test",
        admin_ids=frozenset({1}),
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        redis_url=None,
        redis_key_prefix="humanos-test",
        fsm_ttl_seconds=60,
        session_ttl_seconds=120,
        webhook_base_url=None,
        webhook_secret=None,
        webhook_path="/telegram/webhook",
        webhook_host="127.0.0.1",
        webhook_port=8080,
        webhook_max_connections=100,
        webhook_listen_backlog=2048,
        webhook_drop_pending_updates=False,
        auth_token_secret="test-secret",
        auth_token_ttl_seconds=3600,
        api_shared_secret=None,
        api_rate_limit_max_requests=120,
        api_rate_limit_window_seconds=60,
        analytics_max_file_bytes=5 * 1024 * 1024,
        analytics_backup_count=3,
        analytics_writer_batch_size=200,
        analytics_writer_flush_seconds=0.25,
        analytics_writer_queue_max=200_000,
        aiohttp_connection_limit=300,
        bot_hide_reply_keyboard_outside_home=False,
        bot_identity_resync_seconds=60.0,
    )


@pytest.fixture()
def ctx(settings: Settings) -> AppContext:
    return AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )
