"""
Simple in-memory TTL cache for expensive computations.

KNMI's data updates once a day and station metadata essentially never
changes, so recomputing on every API request is wasteful. This caches a
single value in memory and only recomputes once it's older than ttl_seconds.

Thread-safe via a lock, so concurrent requests during a cache miss don't
both trigger a duplicate (expensive) recompute.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._value: T | None = None
        self._computed_at: float | None = None

    def get(self, compute_fn: Callable[[], T]) -> T:
        with self._lock:
            now = time.monotonic()
            is_stale = (
                self._value is None
                or self._computed_at is None
                or (now - self._computed_at) > self._ttl_seconds
            )
            if is_stale:
                self._value = compute_fn()
                self._computed_at = now
            return self._value

    @property
    def computed_at(self) -> float | None:
        return self._computed_at

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._computed_at = None