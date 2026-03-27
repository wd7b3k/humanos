"""Точка входа для сборки движка протоколов (данные — в ``domain.protocol_engine.PROTOCOLS``)."""

from __future__ import annotations

from domain.protocol_engine import build_default_protocol_engine

__all__ = ["build_default_protocol_engine"]
