"""Shared dependencies for use cases (DI container)."""

from __future__ import annotations

from dataclasses import dataclass

from domain.protocol_engine import ProtocolEngine
from infrastructure.analytics import Analytics
from infrastructure.auth_tokens import AuthTokenCodec
from infrastructure.client_store import ClientStore
from infrastructure.config import Settings
from infrastructure.feedback_store import FeedbackStore
from infrastructure.incidents import IncidentStore
from infrastructure.push import PushTriggerRule
from infrastructure.release_store import ReleaseStore
from infrastructure.storage.repository import UserRepository


@dataclass(slots=True)
class AppContext:
    """Wiring for all use cases — pass this from bot, FastAPI, tests."""

    settings: Settings
    users: UserRepository
    analytics: Analytics
    protocols: ProtocolEngine
    incidents: IncidentStore
    feedback_store: FeedbackStore
    release_store: ReleaseStore
    clients: ClientStore
    auth_tokens: AuthTokenCodec
    push_triggers: tuple[PushTriggerRule, ...]
