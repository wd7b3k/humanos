"""Transport-agnostic auth models for future web/mobile/MAX frontends."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    provider: str
    subject: str
    display_name: str | None = None
    username: str | None = None

    @property
    def actor_id(self) -> str:
        return f"{self.provider}:{self.subject}"


@dataclass(frozen=True, slots=True)
class AuthSession:
    session_id: str
    identity: AuthIdentity
    client_id: str | None
    role: str | None
    scopes: tuple[str, ...]
    issued_at: int
    expires_at: int
