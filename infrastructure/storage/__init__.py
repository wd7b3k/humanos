"""Storage backends."""

from infrastructure.storage.memory import InMemoryUserRepository
from infrastructure.storage.repository import UserRepository

__all__ = ["UserRepository", "InMemoryUserRepository"]
