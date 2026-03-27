"""Small in-memory rate limiter for the HTTP API."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
import time


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    remaining: int


class ApiRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._entries: dict[str, deque[float]] = {}
        self._lock = Lock()

    @property
    def max_requests(self) -> int:
        return self._max_requests

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def check(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        point = now if now is not None else time.time()
        cutoff = point - self._window_seconds
        with self._lock:
            bucket = self._entries.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                retry_after = max(1, int(bucket[0] + self._window_seconds - point))
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=retry_after,
                    remaining=0,
                )
            bucket.append(point)
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
                remaining=max(0, self._max_requests - len(bucket)),
            )
