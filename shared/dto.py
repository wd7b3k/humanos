"""Data transfer objects between layers (no Telegram types)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WelcomeResult:
    """Payload after /start or session reset."""

    text: str
    state_labels: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class StateSelectedResult:
    """User picked a state key."""

    text: str
    state_key: str


@dataclass(frozen=True, slots=True)
class ProtocolStepResult:
    """One step of a protocol."""

    text: str
    step_index: int
    total_steps: int
    is_last_step: bool


@dataclass(frozen=True, slots=True)
class ProtocolStartResult:
    """First step when protocol begins."""

    first_step: ProtocolStepResult


@dataclass(frozen=True, slots=True)
class FinishResult:
    """After final rating and comparison."""

    text: str
    initial_rating: int
    final_rating: int
    improved: bool
    tribute_url: str


@dataclass(frozen=True, slots=True)
class DonationTrackResult:
    """After user asks to open the donation page."""

    url: str
    source: str


@dataclass(frozen=True, slots=True)
class ErrorResult:
    """Recoverable user-facing error."""

    code: str
    message: str
    details: dict[str, Any] | None = None
