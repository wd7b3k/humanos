"""Устаревший модуль: контекст поднимается в ``interfaces.api.main:lifespan`` через ``build_api_context``."""

from __future__ import annotations

from infrastructure.config import load_settings
from infrastructure.runtime import build_api_context


async def create_app_context_async():
    """Для отладки вне FastAPI."""
    return await build_api_context(load_settings())
