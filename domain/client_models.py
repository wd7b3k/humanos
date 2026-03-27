"""Client database models and role constants."""

from __future__ import annotations

from dataclasses import dataclass

ROLE_CLIENT = "client"
ROLE_ADMIN = "admin"
ROLE_SERVICE = "service"
CLIENT_ROLES: tuple[str, ...] = (ROLE_CLIENT, ROLE_ADMIN, ROLE_SERVICE)
INTERNAL_ROLES: frozenset[str] = frozenset({ROLE_ADMIN, ROLE_SERVICE})


def normalize_role(role: str | None, *, default: str = ROLE_CLIENT) -> str:
    raw = (role or "").strip().lower() or default
    if raw not in CLIENT_ROLES:
        raise ValueError(f"unsupported client role: {raw}")
    return raw


@dataclass(frozen=True, slots=True)
class ClientRecord:
    client_id: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ClientIdentityRecord:
    client_id: str
    provider: str
    subject: str
    username: str | None
    display_name: str | None
    profile_url: str | None
    last_seen_at: str | None
