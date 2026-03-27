"""Helpers to map repository dicts to ``UserSessionData``."""

from __future__ import annotations

from domain.models import UserSessionData
from infrastructure.storage.repository import UserRepository


async def load_session(repo: UserRepository, user_id: int | str) -> UserSessionData:
    data = await repo.get(user_id)
    return UserSessionData.from_dict(data)


async def save_session(repo: UserRepository, user_id: int | str, session: UserSessionData) -> None:
    await repo.save(user_id, session.to_dict())
