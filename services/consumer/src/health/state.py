"""Thread-safe health state shared between the poll loop and HTTP probes."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from confluent_kafka import Consumer


@dataclass
class HealthState:
    """
    Tracks liveness signals for Kubernetes-style probes.
    """
    # The time the consumer started. (default_factory =>  Call time.time to create default value)
    started_at: float = field(default_factory=time.time)
    # The time the last poll was made. (This can be either float or None, None is default)
    last_poll_at: float | None = None
    # The time the last successful message was processed. (This can be either float or None, None is default)
    last_success_at: float | None = None
    # Whether the consumer is shutting down. Default is False.
    shutting_down: bool = False
    # The Kafka consumer. (repr=False => Don't show this variable when printing the object)
    _consumer: Consumer | None = field(default=None, repr=False)
    # The lock for the health state. (repr=False => Don't show this variable when printing the object)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_consumer(self, consumer: Consumer) -> None:
        """Attach the Kafka consumer for optional readiness checks."""
        with self._lock:
            self._consumer = consumer

    def touch_poll(self) -> None:
        """Record that the poll loop is still running."""
        with self._lock:
            self.last_poll_at = time.time()

    def touch_success(self) -> None:
        """Record that a message was processed successfully."""
        with self._lock:
            now = time.time()
            self.last_success_at = now
            self.last_poll_at = now

    def set_shutting_down(self) -> None:
        """Mark graceful shutdown so liveness fails and orchestrators restart cleanly."""
        with self._lock:
            self.shutting_down = True

    def is_shutting_down(self) -> bool:
        """
        Return True when a shutdown signal has been received.
        
        ===================== Returns =====================
        True when a shutdown signal has been received.
        False when the consumer is not shutting down.
        """
        with self._lock:
            return self.shutting_down

    def is_alive(self, max_poll_age_seconds: float) -> bool:
        """
        Return True when the consumer loop appears healthy.

        ==================== Arguments ====================
        max_poll_age_seconds: Maximum allowed seconds since the last poll.

        ===================== Returns =====================
        True when the consumer loop appears healthy.
        False when the consumer is shutting down or has not polled yet.
        """
        with self._lock:
            if self.shutting_down:
                return False
            if self.last_poll_at is None:
                return (time.time() - self.started_at) < max_poll_age_seconds
            return (time.time() - self.last_poll_at) < max_poll_age_seconds

    def kafka_has_assignment(self) -> bool:
        """Return True when the consumer has at least one assigned partition."""
        with self._lock:
            if self._consumer is None:
                return False
            try:
                return len(self._consumer.assignment()) > 0
            except Exception:
                return False
