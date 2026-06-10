"""Consumer configuration loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any, Callable
from dataclasses import dataclass
from schemas.events import EVENT_SCHEMAS
from helpers.persistence import EVENT_PERSISTERS

PersistEventFn = Callable[..., None]


@dataclass(frozen=True)
class ConsumerConfig:
    """
    Runtime settings for one consumer instance (ratings or tags stream).
    """

    bootstrap_address: str
    dataset_type: str
    topic: str
    group_id: str
    max_events: int
    log_every_n_events: int
    pipeline_version: str
    event_schema: Any
    persist_event: PersistEventFn

    @classmethod
    def from_env(cls) -> ConsumerConfig:
        """
        Load required settings from the environment.

        ==================== Returns ====================
        A fully populated ConsumerConfig.

        Raises KeyError if a required variable is missing.
        """
        max_events = int(os.environ.get("MAX_EVENTS", "0"))
        log_every_n_events = int(os.environ.get("LOG_EVERY_N_EVENTS", "1000"))
        pipeline_version = os.environ.get("PIPELINE_VERSION", "v1")

        bootstrap_address = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
        dataset_type = os.environ["DATASET_TYPE"]
        topic = os.environ["KAFKA_TOPIC"]
        group_id = os.environ["KAFKA_GROUP_ID"]

        return cls(
            bootstrap_address=bootstrap_address,
            dataset_type=dataset_type,
            topic=topic,
            group_id=group_id,
            max_events=max_events,
            log_every_n_events=log_every_n_events,
            pipeline_version=pipeline_version,
            event_schema=EVENT_SCHEMAS[dataset_type],
            persist_event=EVENT_PERSISTERS[dataset_type],
        )

    def startup_log_extra(self) -> dict[str, Any]:
        """
        This is used to structure the log message when the consumer starts.
        The log message can be used to identify the consumer instance.
        
        E.g: "Starting dataset consumer" with the following structured fields:
        {
            "bootstrap_servers": "kafka:9092",
            "dataset_type": "ratings",
            "topic": "ratings",
            "group_id": "movierec-ratings-consumer",
            "max_events": 0,
            "log_every_n_events": 1000,
            "pipeline_version": "v1",
        }
        
        ==================== Returns ====================
        A dictionary of structured fields to log.
        """
        return {
            "bootstrap_servers": self.bootstrap_address,
            "dataset_type": self.dataset_type,
            "topic": self.topic,
            "group_id": self.group_id,
            "max_events": self.max_events,
            "log_every_n_events": self.log_every_n_events,
            "pipeline_version": self.pipeline_version,
        }
