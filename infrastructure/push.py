"""Future push notification architecture: permissions, triggers, delivery plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PushChannel = Literal["telegram", "web_push", "mobile_push", "email"]


@dataclass(frozen=True, slots=True)
class PushPermission:
    channel: PushChannel
    allowed: bool | None
    source: str
    updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class PushTriggerRule:
    trigger_id: str
    description: str
    channel: PushChannel
    cooldown_seconds: int


@dataclass(frozen=True, slots=True)
class PushEnvelope:
    actor_id: str
    channel: PushChannel
    trigger_id: str
    template_key: str
    payload: dict[str, str]


def default_push_triggers() -> tuple[PushTriggerRule, ...]:
    """Default trigger registry used by future workers / schedulers."""
    return (
        PushTriggerRule(
            trigger_id="protocol_followup_3h",
            description="Follow-up after a helpful protocol",
            channel="telegram",
            cooldown_seconds=3 * 60 * 60,
        ),
        PushTriggerRule(
            trigger_id="inactive_24h",
            description="Gentle return after inactivity",
            channel="telegram",
            cooldown_seconds=24 * 60 * 60,
        ),
        PushTriggerRule(
            trigger_id="feedback_reply",
            description="Team replied to user feedback",
            channel="telegram",
            cooldown_seconds=5 * 60,
        ),
        PushTriggerRule(
            trigger_id="product_update",
            description="Major product update for opted-in users",
            channel="telegram",
            cooldown_seconds=7 * 24 * 60 * 60,
        ),
    )
