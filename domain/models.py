"""Core domain models."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class ProtocolStep:
    """Single actionable step in a protocol."""

    id: str
    title: str
    body: str
    phase: str = ""
    duration_seconds: int = 0
    how_to: str = ""
    alternatives: str | None = None
    goal: str | None = None
    notes: str | None = None
    release_id: str | None = None
    release_version: str | None = None
    variant_id: str | None = None


@dataclass(frozen=True, slots=True)
class Protocol:
    """Named collection of steps."""

    id: str
    name: str
    description: str
    steps: tuple[ProtocolStep, ...]
    release_id: str | None = None
    release_version: str | None = None
    variant_id: str | None = None


@dataclass(frozen=True, slots=True)
class UserSessionData:
    """Persisted per-user session (serialized as dict in repository)."""

    selected_state: str | None = None
    initial_rating: int | None = None
    protocol_id: str | None = None
    protocol_release_id: str | None = None
    protocol_release_version: str | None = None
    protocol_variant_id: str | None = None
    step_index: int = 0
    final_rating: int | None = None
    push_permission_telegram: bool | None = None
    push_permission_answered_at: str | None = None
    feedback_topics: tuple[str, ...] = ()
    feedback_last_message_at: str | None = None
    auth_provider: str = "telegram"
    auth_subject: str | None = None
    telegram_internal_id: str | None = None
    telegram_public_id: str | None = None
    telegram_username: str | None = None
    telegram_profile_url: str | None = None
    telegram_full_name: str | None = None
    telegram_language_code: str | None = None
    telegram_last_seen_at: str | None = None
    client_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "selected_state": self.selected_state,
            "initial_rating": self.initial_rating,
            "protocol_id": self.protocol_id,
            "protocol_release_id": self.protocol_release_id,
            "protocol_release_version": self.protocol_release_version,
            "protocol_variant_id": self.protocol_variant_id,
            "step_index": self.step_index,
            "final_rating": self.final_rating,
            "push_permission_telegram": self.push_permission_telegram,
            "push_permission_answered_at": self.push_permission_answered_at,
            "feedback_topics": list(self.feedback_topics),
            "feedback_last_message_at": self.feedback_last_message_at,
            "auth_provider": self.auth_provider,
            "auth_subject": self.auth_subject,
            "telegram_internal_id": self.telegram_internal_id,
            "telegram_public_id": self.telegram_public_id,
            "telegram_username": self.telegram_username,
            "telegram_profile_url": self.telegram_profile_url,
            "telegram_full_name": self.telegram_full_name,
            "telegram_language_code": self.telegram_language_code,
            "telegram_last_seen_at": self.telegram_last_seen_at,
            "client_id": self.client_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> UserSessionData:
        return cls(
            selected_state=data.get("selected_state"),
            initial_rating=data.get("initial_rating"),
            protocol_id=data.get("protocol_id"),
            protocol_release_id=data.get("protocol_release_id"),
            protocol_release_version=data.get("protocol_release_version"),
            protocol_variant_id=data.get("protocol_variant_id"),
            step_index=int(data.get("step_index") or 0),
            final_rating=data.get("final_rating"),
            push_permission_telegram=data.get("push_permission_telegram"),
            push_permission_answered_at=data.get("push_permission_answered_at"),
            feedback_topics=tuple(data.get("feedback_topics") or ()),
            feedback_last_message_at=data.get("feedback_last_message_at"),
            auth_provider=data.get("auth_provider") or "telegram",
            auth_subject=data.get("auth_subject"),
            telegram_internal_id=data.get("telegram_internal_id"),
            telegram_public_id=data.get("telegram_public_id"),
            telegram_username=data.get("telegram_username"),
            telegram_profile_url=data.get("telegram_profile_url"),
            telegram_full_name=data.get("telegram_full_name"),
            telegram_language_code=data.get("telegram_language_code"),
            telegram_last_seen_at=data.get("telegram_last_seen_at"),
            client_id=data.get("client_id"),
        )

    def with_updates(self, **changes) -> UserSessionData:
        return replace(self, **changes)

    def reset_flow(self) -> UserSessionData:
        return replace(
            self,
            selected_state=None,
            initial_rating=None,
            protocol_id=None,
            protocol_release_id=None,
            protocol_release_version=None,
            protocol_variant_id=None,
            step_index=0,
            final_rating=None,
        )
