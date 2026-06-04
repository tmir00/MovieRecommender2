"""Insert validated events into Postgres (SQLAlchemy Core)."""

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from db.models import ratings_events, tag_events
from schemas.events import RatingEvent, TagEvent


def _rating_event_id(event: RatingEvent) -> str:
    """Stable id so re-consuming the same Kafka message does not duplicate rows."""
    return f"rating.created:{event.user_id}:{event.movie_id}:{event.timestamp}"


def _tag_event_id(event: TagEvent) -> str:
    return f"tag.created:{event.user_id}:{event.movie_id}:{event.timestamp}:{event.tag}"


def persist_rating_event(
    connection: Connection,
    event: RatingEvent,
    *,
    pipeline_version: str,
) -> None:
    """
    Insert one rating event (ignore if event_id already exists).

    ==================== Arguments ====================
    connection: Active SQLAlchemy Core connection.
    event: Validated rating payload from Kafka.
    pipeline_version: Pipeline label stored on each row (e.g. v1).
    """
    stmt = (
        insert(ratings_events)
        .values(
            event_id=_rating_event_id(event),
            user_id=event.user_id,
            movie_id=event.movie_id,
            rating=event.rating,
            rating_timestamp=event.timestamp,
            pipeline_version=pipeline_version,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    connection.execute(stmt)


def persist_tag_event(
    connection: Connection,
    event: TagEvent,
    *,
    pipeline_version: str,
) -> None:
    """
    Insert one tag event (ignore if event_id already exists).

    ==================== Arguments ====================
    connection: Active SQLAlchemy Core connection.
    event: Validated tag payload from Kafka.
    pipeline_version: Pipeline label stored on each row (e.g. v1).
    """
    stmt = (
        insert(tag_events)
        .values(
            event_id=_tag_event_id(event),
            user_id=event.user_id,
            movie_id=event.movie_id,
            tag=event.tag,
            tag_timestamp=event.timestamp,
            pipeline_version=pipeline_version,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    connection.execute(stmt)


EVENT_PERSISTERS = {
    "ratings": persist_rating_event,
    "tags": persist_tag_event,
}
