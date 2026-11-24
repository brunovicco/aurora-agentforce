"""Bounded, process-local admission control for the private broker endpoint."""

from collections.abc import Callable
from threading import Lock
from time import monotonic


class BrokerRateLimit:
    """Global fixed-window request budget; no attacker-controlled bucket keys."""

    def __init__(self, limit: int = 120, *, clock: Callable[[], float] = monotonic) -> None:
        """Configure the request budget per sixty-second window."""
        if limit < 1:
            raise ValueError("Broker request limit must be positive.")
        self._limit = limit
        self._clock = clock
        self._start = clock()
        self._count = 0
        self._lock = Lock()

    def admit(self) -> bool:
        """Count requests, including invalid credentials, before broker lookup."""
        with self._lock:
            now = self._clock()
            if now - self._start >= 60:
                self._start = now
                self._count = 0
            if self._count >= self._limit:
                return False
            self._count += 1
            return True
