"""Pydantic models for Kafka event payloads (must match producer output)."""

from typing import Literal

from pydantic import BaseModel, Field


class RatingEvent(BaseModel):
    """
    A rating event from the ratings topic.

    Validates the JSON shape produced by the ratings producer before we insert
    into `ratings_events`.
    """

    event_type: Literal["rating.created"]
    user_id: int = Field(ge=1)
    movie_id: int = Field(ge=1)
    rating: float = Field(ge=0.5, le=5.0)
    timestamp: int = Field(ge=0)


class TagEvent(BaseModel):
    """
    A tag event from the tags topic.

    Validates the JSON shape produced by the tags producer before we insert
    into `tag_events`.
    """

    event_type: Literal["tag.created"]
    user_id: int = Field(ge=1)
    movie_id: int = Field(ge=1)
    tag: str = Field(min_length=1)
    timestamp: int = Field(ge=0)


EVENT_SCHEMAS = {
    "ratings": RatingEvent,
    "tags": TagEvent,
}
