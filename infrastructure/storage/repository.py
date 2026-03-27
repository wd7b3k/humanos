"""User session persistence abstraction (Redis / PostgreSQL ready)."""

from __future__ import annotations

from typing import Any, Protocol


class UserRepository(Protocol):
    """
    Async port for user-bound session data.

    Реализации: ``InMemoryUserRepository``, ``FileUserRepository``, ``RedisUserRepository``.
    """

    async def get(self, user_id: int | str) -> dict[str, Any]:
        """Return a mutable dict; default empty session if missing."""
        ...

    async def save(self, user_id: int | str, data: dict[str, Any]) -> None:
        """Persist full session snapshot."""
        ...
