"""Event and dead-letter writes against ratings_events, tag_events, and dead_letter_events."""

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert
from shared.db.models import dead_letter_events, ratings_events, tag_events


def rating_event_id(user_id: int, movie_id: int, timestamp: int) -> str:
    """Stable id so re-consuming the same Kafka message does not duplicate rows."""
    return f"rating.created:{user_id}:{movie_id}:{timestamp}"


def tag_event_id(user_id: int, movie_id: int, timestamp: int, tag: str) -> str:
    """Stable id so re-consuming the same Kafka message does not duplicate rows."""
    return f"tag.created:{user_id}:{movie_id}:{timestamp}:{tag}"


def insert_rating_event(connection: Connection, *, event_id: str, user_id: int, movie_id: int, \
                        rating: Decimal | float, rating_timestamp: int, \
                        pipeline_version: str) -> None:
    """
    Insert one rating event into the ratings_events table (ignore if event_id already exists).

    ============================ Arguments ============================
    connection: Active SQLAlchemy Core connection.
    event_id: Stable event id for idempotent inserts.
    user_id: User id from the rating event.
    movie_id: Movie id from the rating event.
    rating: Rating value.
    rating_timestamp: Event timestamp from the source.
    pipeline_version: Pipeline label stored on each row (e.g. v1).
    """
    stmt = (
        insert(ratings_events)
        .values(
            event_id=event_id,
            user_id=user_id,
            movie_id=movie_id,
            rating=rating,
            rating_timestamp=rating_timestamp,
            pipeline_version=pipeline_version,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    connection.execute(stmt)


def insert_tag_event(connection: Connection, *, event_id: str, user_id: int, movie_id: int, \
                    tag: str, tag_timestamp: int, pipeline_version: str) -> None:
    """
    Insert one tag event into the tag_events table (ignore if event_id already exists).

    ==================== Arguments ====================
    connection: Active SQLAlchemy Core connection.
    event_id: Stable event id for idempotent inserts.
    user_id: User id from the tag event.
    movie_id: Movie id from the tag event.
    tag: Tag text.
    tag_timestamp: Event timestamp from the source.
    pipeline_version: Pipeline label stored on each row (e.g. v1).
    """
    stmt = (
        insert(tag_events)
        .values(
            event_id=event_id,
            user_id=user_id,
            movie_id=movie_id,
            tag=tag,
            tag_timestamp=tag_timestamp,
            pipeline_version=pipeline_version,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    connection.execute(stmt)


def insert_dead_letter_event(connection: Connection, *, source_topic: str, source_partition: int, \
                            source_offset: int, consumer_group: str, error_type: str, \
                            error_message: str, payload: str | None) -> None:
    """
    Insert one failed message into dead_letter_events.

    ==================== Arguments ====================
    connection: Active SQLAlchemy Core connection.
    source_topic: Kafka topic the message came from.
    source_partition: Kafka partition the message came from.
    source_offset: Kafka offset of the failed message.
    consumer_group: Consumer group id (for tracing which reader failed).
    error_type: Short category (e.g. json_decode_error, validation_error).
    error_message: Human-readable error detail.
    payload: Raw or serialized message body.
    """
    stmt = insert(dead_letter_events).values(
        source_topic=source_topic,
        source_partition=source_partition,
        source_offset=source_offset,
        consumer_group=consumer_group,
        error_type=error_type,
        error_message=error_message,
        payload=payload,
    )
    connection.execute(stmt)
